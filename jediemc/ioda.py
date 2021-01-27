import ioda
import numpy as np
import os
import glob
import datetime as dt


class ObsSpace:

    def __repr__(self):
        return f"ObsSpace({self.name},{self.iodafiles})"

    def __str__(self):
        return f"IODA ObsSpace Object - {self.name}"

    def __init__(self, path, name='NoName', iodalayout=0):
        self.name = name
        self.layout = iodalayout
        # determine if path is a file or wildcard
        if os.path.isfile(path):
            self.iodafiles = [path]
        elif os.path.isfile(glob.glob(path + '*')[0]):
            self.iodafiles = sorted(glob.glob(path + '*'))
        else:
            raise OSError(f"{path} does not specify a valid path to file(s)")
        # grab lat, lon
        # we will naively assume that all obs spaces will have these
        # store them in .self and use them for length of obs space, etc.
        # not grabbing times yet because it is slow...
        _lats = []
        _lons = []
        for f in self.iodafiles:
            og = self._open_ioda_obsgroup(f)
            iodavar = og.vars.open("latitude@MetaData")
            values = iodavar.readVector.float()
            _lats.append(values)
            iodavar = og.vars.open("longitude@MetaData")
            values = iodavar.readVector.float()
            _lons.append(values)
        # the var list comes in as just a print/string, split it into a list
        _varlist = og.vars.list
        self.varnames = str(_varlist)[55:-3].split()
        self.nvars = len(self.varnames)
        self.lats = np.concatenate(_lats, axis=0)
        self.lons = np.concatenate(_lons, axis=0)
        self.nlocs = len(self.lats)
        del _lats
        del _lons

    def get_variable(self, varname):
        """
        grab the data from this obs space for a requested string 'varname'
        returns numpy array of either floats or integers depending on
        type of requested variable
        """
        # NOTE/TODO: revisit this with a 2D array, probaby need readNPArray...
        _data = []
        for f in self.iodafiles:
            og = self._open_ioda_obsgroup(f)
            iodavar = og.vars.open(varname)
            # determine if float or int
            if iodavar.isA2(ioda._ioda_python.Types.float):
                values = iodavar.readVector.float()
                _data.append(values)
            elif iodavar.isA2(ioda._ioda_python.Types.int):
                values = iodavar.readVector.int()
                _data.append(values)
            else:
                raise TypeError("Only float and int supported for now")
        data = np.concatenate(_data, axis=0)
        data[data > 9e36] = np.nan
        return data

    def get_datetimes(self):
        """
        grab the date / time of each observation in this obs space
        returns a list of datetime objects
        """
        _times = []
        for f in self.iodafiles:
            og = self._open_ioda_obsgroup(f)
            iodavar = og.vars.open("datetime@MetaData")
            values = iodavar.readVector.str()
            # comes as a list of characters, need to combine and
            # make into datetime objects
            i = 0
            while i < len(values):
                joinstr = ''.join(values[i:i+20])
                _times.append(dt.datetime.strptime(joinstr,
                                                   "%Y-%m-%dT%H:%M:%SZ"))
                i += 20
        datetimes = np.array(_times, dtype='datetime64')
        del _times
        return datetimes

    def __len__(self):
        return len(self.lats)

    def _open_ioda_obsgroup(self, filepath):
        # open the obs group for a specified file and return an object
        g = ioda.Engines.HH.openFile(
                        name=filepath,
                        mode=ioda.Engines.BackendOpenModes.Read_Only,
                        )
        dlp = ioda._ioda_python.DLP.DataLayoutPolicy.generate(
                  ioda._ioda_python.DLP.DataLayoutPolicy.Policies(self.layout))
        og = ioda.ObsGroup(g, dlp)
        return og
