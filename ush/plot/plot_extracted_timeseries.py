#!/usr/bin/env python
import yaml
import argparse
import numpy as np
import netCDF4 as nc
import datetime as dt
import matplotlib
matplotlib.use('agg')
from matplotlib import pyplot as plt


def plot_timeseries(timeseries, plotdict):
    """
    plot_timeseries(timeseries, outfile)
    plot_timeseries takes as input a list of dictionaries containing:
    timeseries = [data = {}]
    data['label'] - string of label for line to plot
    data['datafile'] - path to input preprocessed archived data file
    data['dataformat'] - should be 'netcdf' or 'csv'
    data['color'] - string of color of line
    data['varname'] - string of name of variable to plot in archive file

    as well as a dictionary containing overall plot settings
    plotdict['outfile'] - string to where to save figure to
    """
    # create figure
    fig1 = plt.figure(figsize=(10, 8))

    for t in timeseries:
        x, y = read_timeseries(t['datafile'], t['dataformat'], t['varname'])
        plt.plot_date(x, y, color=t['color'], label=t['label'],
                      linestyle='-')

    # add legend, etc.
    plt.legend()
    plt.ylabel(plotdict['ylabel'])
    plt.title(plotdict['title'])

    # save figure
    plt.savefig(plotdict['outfile'])


def read_timeseries(datafile, dataformat, varname):
    # determine if the file is csv or netCDF
    if dataformat == 'csv':
        times = []
        values = []
        with open(datafile, 'r') as f:
            # get matching column
            columns = f.readline().split(',')
            idx = columns.index(varname)
            for line in f:
                data = line.split(',')
                times.append(data[0])
                values.append(float(data[idx]))
        times = [dt.datetime.strptime(time, "%Y%m%d%H") for time in times]
    elif dataformat == 'netcdf':
        with nc.Dataset(datafile, mode='r') as ncf:
            times = ncf.variables['timestamp'][:]
            times = [time.tostring().decode("utf-8") for time in times]
            times = [dt.datetime.strptime(time, "%Y%m%d%H") for time in times]
            values = ncf.variables[varname][:]
    else:
        raise ValueError("dataformat must be 'csv' or 'netcdf'")

    return times, values



if __name__ == '__main__':
    # get input YAML file from command line
    parser = argparse.ArgumentParser(description=(
                                     'This utility will take ',
                                     'an input YAML configuration file ',
                                     'and plot timeseries of specified ',
                                     'variables from archived files ',
                                     'previously generated'))
    parser.add_argument('-y', '--yaml',
                        help='path to input YAML configuration file',
                        required=True)
    args = parser.parse_args()

    # parse YAML file to dictionary
    with open(args.yaml, 'r') as stream:
        config = yaml.safe_load(stream)

    timeseries = config['plot_timeseries']
    plotdict = config['plot_settings']
    plot_timeseries(timeseries, plotdict)
