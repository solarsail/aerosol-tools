# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 21:25:53 2016

@author: 欣晔
"""
import numpy as np

from pyproj import Proj
from pyresample import kd_tree, geometry # 重采样


def get_utm_zone(lon, lat):
    '''
    根据经纬度坐标计算 UTM 投影区域编号。
    只在 UTM 投影中使用。
    '''
    zone = None
    zone_lon = str(lon / 6 + 30)
    
    if lat > 84:
        zone = 'Y' if zone_lon < 0 else 'Z'
    elif lat > 72:
        zone_lat = 'X'
        if 0 <= lon < 9:
            zone_lon = '31'
        elif 9 <= lon < 21:
            zone_lon = '33'
        elif 21 <= lon < 33:
            zone_lon = '35'
        elif 33 <= lon < 52:
            zone_lon = '37'
    elif lat < -80:
        zone = 'A' if zone_lon < 0 else 'B'
    else:
        zone_lat = chr(lat / 8 + ord('N'))
    if zone is None:
        zone = zone_lon + zone_lat
    return zone
    
    
def get_swath_def(data):
    return geometry.SwathDefinition(lons=data.lon, lats=data.lat)
    
    
def get_proj_area(lon_min, lon_max, lat_min, lat_max, proj='merc', zone=None, scale=4000):
    '''
    计算投影范围。
    可以使用麦卡托投影（proj='merc'）或 UTM 投影（proj='utm'）（WGS84坐标系）。
    '''
    lon_center = int(lon_max + lon_min) / 2
    lat_center = int(lat_max + lat_min) / 2
    proj_param = None
    if proj == 'merc':
        proj = Proj(proj='merc', lat_ts=lat_center, lon_0=lon_center)
        proj_param = {'lat_ts': str(lat_center), 'lon_0': str(lon_center), 'proj': 'merc'}
    elif proj == 'utm':
        if zone is None:
            zone = get_utm_zone(lon_center, lat_center)
        proj = Proj(proj='utm', zone=zone, ellps='WGS84', unit='m')
        proj_param = {'ellps': 'WGS84', 'zone': str(zone), 'proj': 'utm'}
        
    lons = [lon_min, lon_max]
    lats = [lat_min, lat_max]
    x, y = proj(lons, lats)
    width = int((x[1]-x[0])/scale)
    height = int((y[1]-y[0])/scale)
    print("figure size: %d x %d" % (width, height))
    
    area_extent = [x[0], y[0], x[1], y[1]]
    area_def = geometry.AreaDefinition('area1', 'Target Area', 'area1',
                               proj_param, width, height, area_extent)
                               
    return area_def
    
    
def get_area_def(data):
    '''
    获取文件经纬度范围的区域定义。
    '''
    lon_min, lon_max = data.lon_range()
    lat_min, lat_max = data.lat_range()
    area_def = get_proj_area(lon_min=lon_min, lon_max=lon_max,
                             lat_min=lat_min, lat_max=lat_max)
    return area_def
    
    
def data_reproject(data, area_def = None):
    '''
    将文件数据投影到指定区域。默认为数据本身的经纬度范围。
    返回一个掩膜数组，无效值被遮盖。
    '''
    if area_def is None:
        area_def = get_area_def(data)
    result = kd_tree.resample_nearest(get_swath_def(data), data.aot_550, area_def, radius_of_influence=5000)
    return np.ma.masked_equal(result, 0)
    
    
def group_reproject(group, area_def = None):
    '''
    将组内所有文件数据投影到指定区域。默认为所有文件经纬度范围的外接矩形。
    返回一个掩膜数组，无效值被遮盖。
    '''
    if area_def is None:
        area_def = get_area_def(group)
        
    base_mask_aot = np.ma.masked_all(area_def.shape)
    # 将每一个AOT填充到大的图像范围内
    for data in group.datasets:     
        print('{} [{}]'.format(data.path, 'processing' if data.valid else 'skipped'))
        if data.valid:
            mask_aot = data_reproject(data, area_def)
            base_mask_aot[base_mask_aot.mask] = mask_aot[base_mask_aot.mask]
          
    return  base_mask_aot  