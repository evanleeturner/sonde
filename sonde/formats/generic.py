"""
    sonde.formats.generic
    ~~~~~~~~~~~~~~~~~

    This module implements a generic format.
    The files are in .csv format and must conform to the
    following guidelines
    comments and metadata at top of file in the format:
      # name: value
    a timezone field: (UTC-?, the data must all be in one UTC offset)
      # timezone: UTC-6
    a fill_value field:
      # fill_value = -999.99
    the last two comment/header lines should be the following
    parameter header prepended by single #:
      # datetime, ATM01, CON01, etc
      (datetime must be first field and in format yyyy/mm/dd HH:MM:SS)
      (parameter names must be from master_param_list
    unit header prepended by single #:
      yyyy/mm/dd HH:MM:SS, Pa, mS/cm, PSU, degC, mH2O, n/a, n/a, n/a
      (units must be from supported_units_list)
    comma seperated data

    special columns or header items:
        original_data_file_name, instrument_manufacturer, instrument_serial_number
        if these exist they will overide self.manufacturer,
        self.data_file and self_serial_number

"""
from __future__ import absolute_import

import datetime
import pkg_resources
import re
from StringIO import StringIO
import xlrd
import csv

import numpy as np
import quantities as pq

from .. import sonde
from .. import quantities as sq
from ..timezones import cdt, cst

class GenericDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a generic csv
    file. 
    """
    def __init__(self, data_file):
        self.manufacturer = 'generic'
        self.file_format = 'generic'
        self.data_file = data_file
        self.format_parameters={}
        fid = open(data_file)
        buf = fid.readline().strip('# ')
        while buf:
            if buf[0:8].lower()=='datetime':
                params = buf.split(',')
                units =  fid.readline().strip('# ').split(',')
                break

            key,val = buf.split(':')
            self.format_parameters[key.strip()]=val.strip()

        utc_offset = int(format_parameters['timezone'].lower().strip('utc'))
        self.default_tzinfo = sonde.UTCStaticOffset(utc_offset)

        data = np.genfromtxt(fid, dtype=None, names=params, delimiter=',')
        self.dates = np.array(
            [datetime.datetime.strptime(dt, '%Y/%m/%d %H:%M:%S')
             for dt in data['datetime']]
            )

        self.dates = [i.replace(tzinfo=self.default_tzinfo) for i in self.dates]

        for param,unit in zip(params,units):
            if unit!='n/a':
                if param.lower() in sonde.master_param_list:
                    self.parameters[param] = param
                else:
                    print 'Unknown Parameter: ', param
                    raise

                #look for unit
                self.data[unit] = parameter.data * punit

        #assign values from header
        super(GenericDataset, self).__init__()


    def _read_data(self):
        """
        Read the solinst data file
        """
        param_map = {'TEMPERATURE' : 'TEM01',
                     'Temperature' : 'TEM01',
                     '1: Conductivity' : 'CON01',
                     'LEVEL' : 'WSE01',
                     'Level' : 'WSE01',
                     'pressure?' : 'ATM01',
                     }

        unit_map = {'Deg C' : pq.degC,
                    'DEG C' : pq.degC,
                    'm' : sq.mH2O,
                    'ft': sq.ftH2O,
                    'mS/cm' : sq.mScm,
                    }

        solinst_data = SolinstReader(self.data_file, self.default_tzinfo)

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()

        for parameter in solinst_data.parameters:
            try:
                pcode = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]
                #ignore params that have no data
                if not np.all(np.isnan(parameter.data)):
                    
            except:
                print 'Un-mapped Parameter/Unit Type'
                print 'Solinst Parameter Name:', parameter.name
                print 'Solinst Unit Name:', parameter.unit
                raise


        self.format_parameters = {
            'serial_number' : solinst_data.serial_number,
            'project_id' : solinst_data.project_id,
            'site_name' : solinst_data.site_name,
            }

        self.dates = solinst_data.dates

class SolinstReader:
    """
    A reader object that opens and reads a Solinst lev file.

    `data_file` should be either a file path string or a file-like
    object. It accepts one optional parameter, `tzinfo` is a
    datetime.tzinfo object that represents the timezone of the
    timestamps in the txt file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.default_tzinfo = tzinfo
        self.num_params = 0
        self.parameters = []
        self.read_solinst(data_file)
        if tzinfo:
            self.dates = [i.replace(tzinfo=tzinfo) for i in self.dates]

    def read_solinst(self, data_file):
        """
        Open and read a Solinst file.
        """
        if type(data_file) == str:
            fid = open(data_file, 'r')

        else:
            fid = data_file

        #read header
        buf = fid.readline().strip(' \r\n')
        params = []
        units = []
        start_reading = False
        while buf:
            if buf=='[Instrument info from data header]':
                start_reading = True

            if not start_reading:
                buf = fid.readline().strip(' \r\n')
                continue

            if buf=='[Data]':
                self.num_rows = int(fid.readline().strip(' \r\n'))
                break

            fields = buf.split('=', 1)

            if fields[0].strip()=='Instrument type':
                self.model = fields[1].strip()

            if fields[0].strip()=='Serial number':
                self.serial_number = fields[1].strip('. ').split()[0].split('-')[-1]

            if fields[0].strip()=='Instrument number':
                self.project_id = fields[1].strip()

            if fields[0].strip()=='Location':
                self.site_name = fields[1].strip()

            if fields[0].strip()=='Identification':
                params.append(fields[1])
                buf = fid.readline().strip(' \r\n')
                fields = buf.split('=', 1)
                if fields[0].strip()=='Unit':
                    units.append(fields[1].strip())
                elif fields[0].strip()=='Reference':
                    #assumes unit field is seperate by at least two spaces. single
                    #space is considered part of unit name
                    units.append(re.sub('\s{1,} ', ',', fields[1]).split(',')[-1])

            buf = fid.readline().strip(' \r\n')

        #skip over rest of header
        #while buf:
        #    if buf=='[Data]':
        #        self.num_rows = int(fid.readline().strip(' \r\n'))
        #        break
        #
        #    buf = fid.readline().strip(' \r\n')

        fields = ['Date','Time'] + params

        #below command is skipping last line of data
        #data = np.genfromtxt(fid, dtype=None, names=fields, skip_footer=1)
        buf = fid.read()
        data = np.genfromtxt(StringIO(buf.split('END')[0]), dtype=None, names=fields)

        self.dates = np.array(
            [datetime.datetime.strptime(d + t, '%Y/%m/%d%H:%M:%S.0')
             for d,t in zip(data['Date'],data['Time'])]
            )

        #assign param & unit names
        for param,unit in zip(params,units):
            self.num_params += 1
            self.parameters.append(Parameter(param.strip(), unit.strip()))

        for ii in range(self.num_params):
            param = re.sub('[?.:]', '', self.parameters[ii].name).replace(' ','_')
            self.parameters[ii].data = data[param]


class Parameter:
    """
    Class that implements the a structure to return a parameters
    name, unit and data
    """
    def __init__(self, param_name, param_unit):

        self.name = param_name
        self.unit = param_unit
        self.data = []