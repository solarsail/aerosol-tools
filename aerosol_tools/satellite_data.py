# -*- coding: utf-8 -*-
"""
Created on Tue Mar 29 22:59:42 2016

@author: 欣晔
"""

import datetime
import math
import os

import h5py
import pyhdf

import numpy as np

from collections import defaultdict

from pyhdf import SD



def distance(p1, p2):
    return math.sqrt(math.pow((p1[0]-p2[0]), 2) + math.pow((p1[1]-p2[1]), 2))
    

class FileError:
    def __init__(self, path):
        self.path = path
        
    def __str__(self):
        return 'Unable to open file: {}'.format(self.path)
        
        
class BadFileHandler(object):
    def __init__(self, halt=False):
        self.halt = halt
        
    def handle(self, path):
        pass
        
    
class NullHandler(BadFileHandler):
    def __init__(self):
        super(NullHandler, self).__init__()


class LogHandler(BadFileHandler):
    def __init__(self, logfile, halt=False):
        super(LogHandler, self).__init__(halt)
        self.logfile = logfile
        
    def handle(self, path):
        with open(self.logfile, 'a') as lf:
            lf.write(path + '\n')
        if self.halt:
            raise FileError(path)
        
        
class SatelliteData(object):
    # 寻找指定坐标时，最接近的数据点与所查找点的直线距离不能超过此值（角度）
    approx_threshold = 1
    # 对错误文件的处理
    bad_file_handler = NullHandler()
    # 像素分辨率（千米）
    resolution = 1
    
    def __init__(self, path, value_cap):
        self.path = path.encode('ascii')
        self.filename = os.path.split(self.path)[1]
        self.valid = False
        self.aot_550 = None
        self.lat = None
        self.lon = None 
        self.value_cap = value_cap
        
    def lon_range(self):
        return (self.lon.min(), self.lon.max())
        
    def lat_range(self):
        return (self.lat.min(), self.lat.max())
        
    def locate(self, lon, lat):
        """在数据中查找与指定坐标最接近的坐标点索引，以及该点的坐标值。"""
        dlon = np.square(np.abs(self.lon - lon))
        dlat = np.square(np.abs(self.lat - lat))
        dist = np.add(dlon,dlat)
        flat_index = np.argmin(dist)
        index = np.array(np.unravel_index(flat_index, dist.shape))
        return index, (self.lon[index], self.lat[index])
        
    def area_average(self, lon, lat, diameter):
        index, coord = self.locate(lon, lat)
        if distance(coord, (lon, lat)) > self.approx_threshold:
            # 不在数据范围内
            return None
        else:
            x, y = index
            r = math.ceil((diameter / self.resolution - 1) / 2)
            area = self.aot_550[x-r:x+r+1, y-r:y+r+1]
            count = np.count_nonzero(area)
            avg = np.sum(area) / count
            # 部分超出数据边界将不做特殊处理
            return avg
        
        
class ModisData(SatelliteData):
    
    # Modis数据固定值，scale=0.001，offset=0
    scale = 0.001
    
    def __init__(self, path, value_cap):
        
        def scale(data, fill_value = 0):
            data[data == -9999] = fill_value # -9999为无效点
            raw_limit = self.value_cap / self.scale
            data[data > raw_limit] = raw_limit # 设置 aod 最大值
            data = data.astype(float)
            data *= self.scale
            return data
            
        super(ModisData, self).__init__(path, value_cap)
        try:
            obj = SD.SD(self.path, SD.SDC.READ)
            self.lon = obj.select('Longitude').get()
            self.lat = obj.select('Latitude').get()
            aot_550 = obj.select('Optical_Depth_Land_And_Ocean').get()
            self.aot_550 = scale(aot_550)
            self.valid = True
        except pyhdf.error.HDF4Error:
            self.bad_file_handler.handle(self.path)
                
    def date(self):
        return get_file_date(self.filename, 'modis')
                
    
class ViirsData(SatelliteData):
    def __init__(self, path, value_cap):
        
        def scale(data, fill_value = 0):
            raw_limit = (self.value_cap - self.offset) / self.scale
            data[data >= 65528] = fill_value # 65528或以上为无效点
            data[data > raw_limit] = raw_limit # 设置 aod 最大值
            data = data.astype(float)
            data *= self.scale
            data += self.offset
            data[data < 0] = 0
            return data
            
        super(ViirsData, self).__init__(path, value_cap)
        try:
            f = h5py.File(path, 'r')
            geo_dataset = f['/All_Data/VIIRS-Aeros-EDR-GEO_All']
            aero_dataset = f['/All_Data/VIIRS-Aeros-EDR_All']
            factors = aero_dataset['AerosolOpticalDepthFactors'].value
            aot_550 = aero_dataset['AerosolOpticalDepth_at_550nm'].value
            self.lat = geo_dataset['Latitude'].value
            self.lon = geo_dataset['Longitude'].value
            # 如果数据中没有有效值，或者经纬度有无效值，则将该文件设为无效
            if aot_550.min() < 65528 and self.lat.min() >= -90 and self.lat.max() <= 90:
                self.scale = factors[0]
                self.offset = factors[1]
                self.aot_550 = scale(aot_550)
                self.valid = True
        except IOError:
            self.bad_file_handler.handle(self.path)
            
    def date(self):
        return get_file_date(self.filename, 'viirs')


class DataGroup(object):
    def __init__(self, filelist, data_class, value_cap):
        self.datasets = [data_class(name, value_cap) for name in filelist]
        self.lat_max = max([f.lat.max() for f in self.datasets if f.valid])
        self.lat_min = min([f.lat.min() for f in self.datasets if f.valid])
        self.lon_max = max([f.lon.max() for f in self.datasets if f.valid])
        self.lon_min = min([f.lon.min() for f in self.datasets if f.valid])
    
    def lon_range(self):
        return (self.lon_min, self.lon_max)
        
    def lat_range(self):
        return (self.lat_min, self.lat_max)


def get_file_date(filename, filetype):
    if filetype == 'modis':
        year = int(filename[10:14])
        julian_day = int(filename[14:17])
        file_date = datetime.datetime(year, 1, 1) + datetime.timedelta(julian_day-1)
        date = file_date.strftime('%Y%m%d')
        return date
    elif filetype == 'viirs':
        return filename[17:25]
    elif filetype == 'merge':
        return filename[7:15]
    else:
        return '19700101'
        
        
def group_files(path, tag='viirs'):
    ext = {
        'viirs': '.h5',
        'modis': '.hdf',
        'merge': '.npz'
    }
    d = defaultdict(list)
    
    filenames = [name for name in os.listdir(path) if name.endswith(ext[tag])]
    for name in filenames:
        d[get_file_date(name, tag)].append(os.path.join(path, name))
    
    return d
    
    
def save_merged(modis, viirs, diff, folder, suffix):
    filename = '_'.join(['merged', suffix])
    filename = os.path.join(folder, filename)
    np.savez_compressed(filename, modis=modis.filled(0), viirs=viirs.filled(0), diff=diff.filled(0))