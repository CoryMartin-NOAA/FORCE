#!/usr/bin/env python
import yaml
import argparse
import glob
import ioda


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
    iodalayout = 1  # is this the right value?
    if 'iodaformat' in obsspace:
        if obsspace['iodaformat'] == 'classic':
            iodalayout = 0
    # get list of available input files
    iodafiles = glob.glob(obsspace['datapath']+'*')
    # dictionary of lists to append to
    ioda = {}
    for vname in obsspace['variables']:
        ioda[vname] = []
    for iodafile in iodafiles:
        iodatmp = read_ioda_obsspace(iodafile, obsspace['variables'],
                                     qcvar=obsspace['qcvar'],
                                     iodalayout=iodalayout)


def read_ioda_obsspace(iodafile, varlist, qcvar=None, iodalayout=0):
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
    for v in varlist:
        iodaVar = og.vars.open(v)
        iodaData = iodaVar.readNPArray.float()
    if qcvar:
        iodaQCVar = og.vars.open(qcvar)
        iodaQC = iodaQCVar.readNPArray.int()
    print(iodaQC)
    print(iodaData)


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
