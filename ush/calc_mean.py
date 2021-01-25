#!/usr/bin/env python
import yaml
import argparse
import glob
import ioda
import numpy as np
import netCDF4 as nc
import os


def calc_mean(obsspace):
    """
    calc_mean takes an input dictionary (obsspace) containing the following:
    obsspace['name'] - name of the obs space
    obsspace['datapath'] - path to glob to get all input IODA files
    obsspace['variables'] - list of strings of variables to compute mean for
    obsspace['outfile'] - output file path
    obsspace['outformat'] - should be 'netcdf' or 'csv'
    obsspace['timestamp'] - datetime object of valid time for data

    The below are optional:
    obsspace['iodaformat'] - classic if non ioda-engines file
    obsspace['qcvar'] - variable to check QC values in
    obsspace['qcvals'] - list of values of QC to keep

    and will compute and save means from JEDI IODA obs spaces
    and put them in an output file for archival
    """
    # IODA engines file layout
    iodalayout = 1  # is this the right value?
    if 'iodaformat' in obsspace:
        if obsspace['iodaformat'] == 'classic':
            iodalayout = 0
    # quality control
    qcvar = None
    qcvals = None
    if 'qcvar' in obsspace:
        qcvar = obsspace['qcvar']
        qcvals = obsspace['qcvals']
    # get list of available input files
    iodafiles = glob.glob(obsspace['datapath']+'*')
    # dictionary of lists to append to
    ioda = {}
    for vname in obsspace['variables']:
        ioda[vname] = []
    if qcvar:
        ioda['QC'] = []
    # read data from IODA and put in dictionary of lists
    for iodafile in iodafiles:
        iodatmp = read_ioda_obsspace(iodafile, obsspace['variables'],
                                     qcvar=qcvar, qcvals=qcvals,
                                     iodalayout=iodalayout)
        for vname in obsspace['variables']:
            ioda[vname].append(iodatmp[vname])
        ioda['QC'].append(iodatmp['QC'])
    # combine each list of arrays into one long numpy array
    for vname in ioda:
        ioda[vname] = np.concatenate(ioda[vname], axis=0)
    # RMSE and MAE
    RMSE = {}
    MAE = {}
    counts = {}
    for vname in obsspace['variables']:
        RMSE[vname] = np.sqrt(((ioda[vname])**2).mean())
        MAE[vname] = np.nanmean(ioda[vname])
        counts[vname] = len(ioda[vname])
    # save this to a specified file
    if obsspace['outformat'] == 'csv':
        # save to csv file
        write_means_csv(obsspace, RMSE, MAE, counts)
    elif obsspace['outformat'] == 'netcdf':
        # save to netCDF file
        write_means_nc(obsspace, RMSE, MAE, counts)
    else:
        raise ValueError("outformat must be 'csv' or 'netcdf'")


def write_means_csv(configdict, RMSE, MAE, counts):
    exists = False
    # first check to see if file exists
    exists = True if os.path.isfile(configdict['outfile']) else False
    with open(configdict['outfile'], 'a') as outfile:
        if not exists:
            outstr = 'cycle,'
            for vname in configdict['variables']:
                outstr = outstr + vname+'_RMSE,'
                outstr = outstr + vname+'_MAE,'
                outstr = outstr + vname+'_counts,'
            outstr = outstr + '\n'
            outfile.write(outstr)
        outstr = configdict['timestamp'].strftime('%Y%m%d%H') + ','
        for vname in configdict['variables']:
            outstr = outstr + f"{RMSE[vname]},{MAE[vname]},{counts[vname]},"
        outstr = outstr + '\n'
        outfile.write(outstr)


def write_means_nc(configdict, RMSE, MAE, counts):
    exists = False
    # first check to see if file exists
    exists = True if os.path.isfile(configdict['outfile']) else False
    if not exists:
        with nc.Dataset(configdict['outfile'], mode='w') as outfile:
            # create dimensions and variables
            time_dim = outfile.createDimension("time", None)
            str_dim = outfile.createDimension("timestrlen", 10)
            timestamp = outfile.createVariable("timestamp", "S1",
                                               ("time", "timestrlen"))
            timestamp.long_name = "valid time in YYYYMMDDHH"
            for vname in configdict['variables']:
                varstr = vname + '_RMSE'
                outvar1 = outfile.createVariable(varstr, "f4", ("time"))
                varstr = vname + '_MAE'
                outvar2 = outfile.createVariable(varstr, "f4", ("time"))
                varstr = vname + '_counts'
                outvar3 = outfile.createVariable(varstr, "i4", ("time"))
    with nc.Dataset(configdict['outfile'], mode='a') as outfile:
        # determine index in unlimited dimension
        timestamp = outfile.variables['timestamp']
        idx = timestamp.shape[0]
        # write out data to file
        tmpstr = np.array(configdict['timestamp'].strftime('%Y%m%d%H'),
                         dtype="S10")
        timestamp[idx,:] = nc.stringtochar(tmpstr)


def read_ioda_obsspace(iodafile, varlist, qcvar=None,
                       qcvals=None, iodalayout=0):
    """
    read_ioda_obsspace will read an IODA obsspace for a given input file
    and return a dictionary of all variables in varlist
    layout supports classic - 0 and ioda-engines - 1 as values
    """
    g = ioda.Engines.HH.openFile(
                   name=iodafile,
                   mode=ioda.Engines.BackendOpenModes.Read_Only,
                   )
    dlp = ioda._ioda_python.DLP.DataLayoutPolicy.generate(
               ioda._ioda_python.DLP.DataLayoutPolicy.Policies(iodalayout))
    og = ioda.ObsGroup(g, dlp)
    iodaout = {}
    if qcvar:
        iodaQCVar = og.vars.open(qcvar)
        iodaQC = iodaQCVar.readNPArray.int()
        goodobs = np.isin(iodaQC, qcvals)
        goodobs = np.where(goodobs)
        iodaQC = iodaQC[goodobs]
        iodaout['QC'] = iodaQC
    for v in varlist:
        iodaVar = og.vars.open(v)
        iodaData = iodaVar.readNPArray.float()
        if qcvar:
            iodaData = iodaData[goodobs]
        iodaout[v] = iodaData
    return iodaout


if __name__ == '__main__':
    # get input YAML file from command line
    parser = argparse.ArgumentParser(description=(
                                     'This utility will take ',
                                     'an input YAML configuration file ',
                                     'and calculate and save means for ',
                                     'specified variables to an output file ',
                                     'for plotting / archiving'))
    parser.add_argument('-y', '--yaml',
                        help='path to input YAML configuration file',
                        required=True)
    args = parser.parse_args()

    # parse YAML file to dictionary
    with open(args.yaml, 'r') as stream:
        config = yaml.safe_load(stream)

    # loop through the list of obs spaces and pass each one to function
    obsspaces = config['calc_mean']
    for obsspace in obsspaces:
        calc_mean(obsspace['obs space'])
