#!/usr/bin/env python
import yaml
import argparse

if __name__ == '__main__':
    # get input YAML file
    parser = argparse.ArgumentParser(description=('This utility will take ',
                                     'an input YAML configuration file ',
                                     'and calculate and save means for ',
                                     'specified variables to an output file ',
                                     'for plotting / archiving'))
    parser.add_argument('-y', '--yaml',
                        help='path to input YAML configuration file',
                        required=True)
    args = parser.parse_args()
