# -*- coding: utf-8 -*-
"""
Created on Thu Jul 21 15:35:54 2011

@author: snegusse
"""
import os
import sys
import platform
import string
from collections import OrderedDict

import numpy as np
import pandas as pd
import sonde

def remove_last_line_from_string(s):
    return s[:s.rfind('\n')]


site_name = raw_input("\nEnter site name: ").lower()
requested_param_list = raw_input('\nEnter comma separated list (no spaces) water quality parameter code to save\n'
                                    '\nParameter Codes\n'
                                    '===============\n'
                                    'Salinity = seawater_salinity\n'
                                    'Water Temperature = water_temperature\n'
                                    '\n: ').lower().split(',')


start_date_str = raw_input('\nEnter the start date(yyyy-mm-dd) of the data range to plot. \n'
                        '[Press enter to plot from first available record]: ')
end_date_str = raw_input('\nEnter the end date(yyyy-mm-dd) of the data range to plot. \n'
                        '[Press enter to plot to end of available record]:')    
freq = raw_input('\nEnter data frequency requested as daily, hourly, etc.\n'
                 '[Press enter to use data frequency]: ')
                        
frequency_map = {'hourly': 'H', 'daily': 'D', 'monthly': 'M'}

param_units = OrderedDict()
for param in requested_param_list:
    if param in sonde.master_parameter_list.keys():
        param_units[param] = sonde.master_parameter_list[param][1].units.symbol
if len(param_units.keys()) == 0:
    sys.exit("The given list of parameters not found. Check the parameter\n"
                "code is correct.")

if platform.system() == 'Windows':
    base_dir = 'T:\BaysEstuaries\Data\WQData'
    output_dir = 'C:\Documents and Settings\SNegusse\Desktop\\for_norman'

if platform.system() == 'Linux':
    base_dir = '/T/BaysEstuaries/Data/WQData'
    output_dir = '/T/BaysEstuaries/USERS/SNegusse/data_requests/rika_galveston_matagorda'
    
sonde_data_file = os.path.join(base_dir,'sites',site_name,'twdb_wq_' + site_name + '.csv' )
   
header = ''
fid = open(sonde_data_file, 'r')
header_line = fid.readline()
while '#' in header_line:
    header += header_line
    header_line = fid.readline()
fid.close()
header = remove_last_line_from_string(remove_last_line_from_string(remove_last_line_from_string(header)))   
sonde_data = sonde.Sonde(sonde_data_file)
sonde_dates = [pd.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                              '%m-%d-%y %H:%M:%S') for dt in 
                              sonde_data.dates]
all_wq_data = pd.DataFrame(sonde_data.data, index=sonde_dates)

if len(start_date_str) == 0:
    start_date = all_wq_data.index[0]
else:
    start_date = pd.datetime.strptime(start_date_str, '%Y-%m-%d')
if len(end_date_str) == 0:
    end_date = all_wq_data.index[-1]
else:
    end_date = pd.datetime.strptime(end_date_str, '%Y-%m-%d')

requested_wq_data = all_wq_data.ix[start_date:end_date, param_units.keys()]
if requested_wq_data.shape[0] == 0:
    sys.exit("No data found for the given date range and parameters.")

for param in param_units.keys():
    if requested_wq_data[param].shape[0] == 0:
        requested_wq_data.drop(param, inplace=True)
#convert data to the desired frequency. the default resampling method is 'mean'.
if freq in frequency_map.keys():
    freq_code = frequency_map[freq]
    requested_wq_data = requested_wq_data.resample(freq_code)

#

requested_data_file = os.path.join(output_dir,site_name + '.csv')
fid =  open(requested_data_file, 'w')
fid.write(header)
fid.write('# datetime,' + string.join(param_units.keys(), ',') + '\n')
fid.write('# yyyy/mm/dd HH:MM:SS,' + string.join(param_units.values(), ',') + '\n')

requested_wq_data.to_csv(fid, mode='a', sep=',', header=None, na_rep='-999.99',
                         date_format='%Y/%m/%d %H:%M:%S', float_format='%5.2f')

fid.close()