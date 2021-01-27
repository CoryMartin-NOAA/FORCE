import netCDF4 as nc
import numpy as np
import os
import glob
import datetime as dt


class CubedSphere:

    def __init__(self, path):
        # determine if path is a file or wildcard
        self._is_glob = False
        if os.path.isfile(path):
            self.fv3files = [path]
        elif os.path.isfile(glob.glob(path + '*')[0]):
            self.fv3files = sorted(glob.glob(path + '*'))
            self._is_glob = True
        else:
            raise OSError(f"{path} does not specify a valid path to file(s)")
        # get times from coupler.res if it is provided
        self.inittime, self.validtime = self._read_coupler()
        # determine if I am global or regional
        self.fv3_global, self.fv3_lam = self._am_i_global()
        self.ntiles = 1 if self.fv3_lam else 6
        # get dictionary of variables and which file they reside in
        self.vardict = self._get_vardict()

    def load_geog(self, path):
        """
        CubedSphere.load_geog(path)
        takes path as an input start of the path of where the FV3 geograhphical
        netCDF files are located to get the lat/lon, etc.
        global example: CubedSphere.load_geog('/path/to/oro_data.*')
        regional example: CubedSphere.load_geog('/path/to/oro_data.tile7.nc')

        will populate self.lons and self.lats
        """
        if self.fv3_lam:
            with nc.Dataset(path, 'r') as ncf:
                self.lons = ncf.variables['geolon'][:]
                self.lats = ncf.variables['geolat'][:]
        if self.fv3_global:
            paths = sorted(glob.glob(path))
            # first get nx and ny from the first file
            with nc.Dataset(paths[0], 'r') as ncf:
                _lons = ncf.variables['geolon'][:]
                _lats = ncf.variables['geolat'][:]
            self.lons = np.empty((6, _lons.shape[0], _lons.shape[1]))
            self.lats = np.empty((6, _lats.shape[0], _lats.shape[1]))
            self.lons[0, ...] = _lons
            self.lats[0, ...] = _lats
            for i in range(1, 6):
                with nc.Dataset(paths[i], 'r') as ncf:
                    self.lons[i, ...] = ncf.variables['geolon'][:]
                    self.lats[i, ...] = ncf.variables['geolat'][:]

    def get_variable(self, varname):
        """
        grab the data from this model state for a requested string 'varname'
        returns either 2D, 3D, or 4D numpy array depending on
        type of requested variable and if the state is 1 or 6 tiles
        """
        if self.fv3_lam:
            with nc.Dataset(self.vardict[varname], 'r') as ncf:
                _vardata = ncf.variables[varname][0, ...]
        if self.fv3_global:
            origpath = self.vardict[varname]
            paths = sorted(glob.glob(origpath.replace('tile1', 'tile*')))
            # get shape from the first file
            with nc.Dataset(paths[0], 'r') as ncf:
                _tmpdata = ncf.variables[varname][:]
            _vardata = np.empty((6,) + _tmpdata.shape[1:])
            _vardata[0, ...] = _tmpdata
            for i in range(1, 6):
                with nc.Dataset(paths[i], 'r') as ncf:
                    _vardata[i, ...] = ncf.variables[varname][0, ...]
        return _vardata

    def _get_vardict(self):
        _vardict = {}
        for rst in self.fv3files:
            if os.path.basename(rst)[-8:] in ['e.res.nc', 'tile1.nc']:
                with nc.Dataset(rst, 'r') as ncf:
                    for vname in ncf.variables:
                        _vardict[vname] = rst
        return _vardict

    def _read_coupler(self):
        _inittime = None
        _validtime = None
        _coupler = None
        for rst in self.fv3files:
            if os.path.basename(rst)[-11:] == 'coupler.res':
                _coupler = rst
        if _coupler:
            with open(_coupler, 'r') as f:
                f.readline()
                _initstr = f.readline().split()[0:6]
                _validstr = f.readline().split()[0:6]
            _it = list(map(int, _initstr))
            _vt = list(map(int, _validstr))
            _inittime = dt.datetime(_it[0], _it[1], _it[2], _it[3], _it[4])
            _validtime = dt.datetime(_vt[0], _vt[1], _vt[2], _vt[3], _vt[4])
        return _inittime, _validtime

    def _am_i_global(self):
        _global = False
        _lam = False
        i1 = 0
        i2 = 0
        for rst in self.fv3files:
            rsttype = os.path.basename(rst).split('.')[-4]
            if rsttype == 'fv_core':
                i1 += 1
            elif rsttype == 'fv_tracer':
                i2 += 1
        if i1 == 1 or i2 == 1:
            _lam = True
        if i1 == 6 or i2 == 6:
            _global = True
        return _global, _lam
