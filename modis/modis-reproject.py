# -*- coding: utf-8 -*-
"""
Created on Sat Feb 13 20:05:11 2016

@author: solar
"""
from __future__ import division
from __future__ import print_function
import glob
import time
import numpy as np
#import matplotlib.pyplot as plt
from PIL import Image
#from trollimage.image import Image
from pycoast import ContourWriterAGG
from pyhdf import SD
from pyproj import Proj
from pyresample import kd_tree, geometry # 重采样
from scipy.interpolate import RegularGridInterpolator as rgi
import math
import json


offset_attr = {
    'reflectance': 'reflectance_offsets',
    'radiance': 'radiance_offsets'
}

scale_attr = {
    'reflectance': 'reflectance_scales',
    'radiance': 'radiance_scales'
}

def read_conf(filename):
    conf = None
    with open(filename) as config:
        conf = json.load(config)
    return conf
    
def get_proj_area(zone, lon_min, lon_max, lat_min, lat_max):
    lons = [lon_min, lon_max]
    lats = [lat_min, lat_max]
    proj = Proj(proj='utm',zone=zone, ellps='WGS84', unit='m')
    x, y = proj(lons, lats)
    width = int((x[1]-x[0])/1000)
    height = int((y[1]-y[0])/1000)
    print("figure size: %d x %d" % (width, height))
    
    area_extent = [x[0], y[0], x[1], y[1]]
    area_def = geometry.AreaDefinition('area1', 'Target Area', 'area1',
                               {'ellps': 'WGS84', 'zone': str(zone),'proj': 'utm'},
                               width, height, area_extent)
                               
    return area_def
    
def get_swath_def(geo_obj):
    x = geo_obj.select('Longitude')[:]
    y = geo_obj.select('Latitude')[:]

    swath_def = geometry.SwathDefinition(lons=x, lats=y)
    return swath_def
    
def get_calibrated_band(L1B_obj, dataset_name, band, mode = 'reflectance'):
    '''
    获取指定波段的观测数据，band 为波段编号，对应波段应在 dataset_name 数据集中存在。
    mode 为 reflectance 和 radiance，获取反射率或辐照度。
    '''
    raw_dataset = L1B_obj.select(dataset_name)
    band_names = raw_dataset.attributes()['band_names'].split(',')
    index = band_names.index(str(band))
    scale = raw_dataset.attributes()[scale_attr[mode]][index]
    offset = raw_dataset.attributes()[offset_attr[mode]][index]
    raw_band = raw_dataset[index]
    
    band = (raw_band - np.ones(raw_band.shape) * offset) * scale
    return band
    
def get_angle_data(L1B_obj):
    '''
    获取角度信息，返回与观测数据相同尺寸的数组。
    每个点的角度数据顺序由 dataset_names 定义
    '''
    dataset_names = ('SolarAzimuth', 'SolarZenith', 'SensorAzimuth', 'SensorZenith')
    angle_data = []
    for name in dataset_names:
        dataset = L1B_obj.select(name)
        scale = dataset.attributes()['scale_factor']
        data = dataset[:] * scale * np.pi / 180
        data = np.repeat(data, 5, axis=1)   # 406 * 271 -> 2030 * 271
        data = np.repeat(data, 5, axis=0)   # 2030 * 271 -> 2030 * 1355
        data = data[:,:-1]  # 2030 * 1355 -> 2030 * 1354
        angle_data.append(data)
        
    angle_data = np.dstack(angle_data)
    return angle_data

def split_data(data, width):
    for i in xrange(0, data.shape[0], width):
        for j in xrange(0, data.shape[1], width):
            yield data[i:i+width, j:j+width]

def NDVI(x,y):
    return (x-y)/(x+y)
    
def get_reflectance_data(L1B_obj):
    c066 = get_calibrated_band(L1B_obj, 'EV_250_Aggr1km_RefSB', '1') # 0.66um 红波段
    c047 = get_calibrated_band(L1B_obj, 'EV_500_Aggr1km_RefSB', '3') # 0.47um 蓝波段
    c055 = get_calibrated_band(L1B_obj, 'EV_500_Aggr1km_RefSB', '4') # 0.55um 绿波段
    c138 = get_calibrated_band(L1B_obj, 'EV_1KM_RefSB', '26') # 1.38um 波段，判断云
    c086 = get_calibrated_band(L1B_obj, 'EV_1KM_RefSB', '16') # 0.86um 波段，判断冰雪
    c124 = get_calibrated_band(L1B_obj, 'EV_500_Aggr1km_RefSB', '5') # 1.24um 波段，判断冰雪
    c212 = get_calibrated_band(L1B_obj, 'EV_500_Aggr1km_RefSB', '7') # 2.12um 波段，判断暗像元
    c1100 = get_calibrated_band(L1B_obj, 'EV_1KM_Emissive', '31','radiance') # 1100um 波段，判断冰雪,取辐亮度数据
    
    
    data = np.dstack((c1100, c212, c138, c124, c086, c066, c055, c047))
    return data
    
def main():
    conf = read_conf("config.txt")
    start = time.clock()
    # 观测数据
    hdf_L1B = glob.glob(conf['mod02-file'])
    L1B_obj = SD.SD(hdf_L1B[0], SD.SDC.READ)
    # 观测点坐标
    hdf_Geo = glob.glob(conf['mod03-file'])
    GEO_obj = SD.SD(hdf_Geo[0], SD.SDC.READ)
    
    swath_def = get_swath_def(GEO_obj)
    data = get_reflectance_data(L1B_obj)
    
    area_def = get_proj_area(zone=50, lon_min=115, lon_max=123, lat_min=37, lat_max=42)
    
    result = kd_tree.resample_nearest(swath_def, data, area_def, radius_of_influence=5000)
   
    
#    plt.axis()
#    plt.imshow(result)
#    plt.savefig(r'D:/mei/result.png')
    
    result = np.uint8(result * 255)
    img = Image.fromarray(result[:,:,4:], 'RGB')
    
    cw = ContourWriterAGG(conf['shp-path'])
    cw.add_coastlines(img, area_def, resolution='i', width=0.5)
    
    img.save(conf['img-output'])
        
    end = time.clock()
    print(end - start)
    
    
    

    
def make_mask(data_box, mask_box, width):
    '''
    创建一个云/冰雪/水体掩膜，存储每个3*3像素是否为云，
    以及每个单独像素是否为云冰雪/水体
    data_box: 数据3*3数组
    mask_box: 掩膜3*3数组
    '''
    std047 = np.std(data_box[:,:,7]) # 0.47um波段的3*3反射率标准差大于0.0025
    std138 = np.std(data_box[:,:,2]) # 1.38um波段的3*3反射率标准差大于0.003
    if std047 > 0.0025 or std138 > 0.003:
        mask_box = np.ones(mask_box.shape)
        return

    for i in range(width):
        for j in range(width):
            NDVI_086_124 = NDVI(data_box[i,j,4], data_box[i,j,3]) #波段顺序c1100, c212, c138, c124, c086, c066, c055, c047
            NDVI_066_086=NDVI(data_box[i,j,5],data_box[i,j,4])
            k1=729.541636 
            k2=1304.413871
            BrightT=k2/np.log(1+k1/data_box[i,j,0])
            if data_box[i,j,7] > 0.4 or data_box[i,j,2] > 0.025: #0.47um波段反射率大于0.4和1.38um波段反射率大于0.025
                mask_box[i,j] = 1    #判断为云
            if NDVI_086_124 > 0.1 and BrightT < 285:   #0.86um和1.24um波段的反射率的NDVI大于0.1，加上温度小于285K
                mask_box[i,j] = 1   #判断冰雪
            if NDVI_066_086 > 0.1:   # 0.66um和0.86um波段的反射率的NDVI大于0.1，判断内陆水
                mask_box[i,j] = 1   
            
def dark_target(data, mask, width):
    '''
    输入多波段反射率数据和掩膜数据，对每个 width * width box 做暗像元提取和合并，
    输出合并后的整幅图像，为下一步反演做准备
    '''
    dark_data = []
    for data_box, mask_box in zip(split_data(data, width), split_data(mask, width)):
        dark = []
        for i in range(width):
            for j in range(width):
                if data_box[i,j,1] < 0.25 and data_box[i,j,1] > 0.01 and mask_box[i,j] == 0:
                    dark.append(data_box[i,j])
        pixel = np.average(dark)
        dark_data.append(pixel)
        
    dark_data = np.array(dark_data)
    dark_data = np.reshape(dark_data, data.shape / width)
    return dark_data
    
def surface_reflectance(Ref212, MVI, ScatAng) :
    Slope_NDVI_066_212=0.48
    if MVI > 0.75:
        Slope_NDVI_066_212 = 0.58
    elif MVI >= 0.25:
        Slope_NDVI_066_212 = 0.48 + 0.2 * (MVI-0.25)
        
    Slope_066_212 = Slope_NDVI_066_212 + 0.002 * ScatAng - 0.27
    yint_066_212 = -0.00025 * ScatAng + 0.033
    Slope_047_066 = 0.49
    yint_047_066 = 0.005
    RefSuf066 = Ref212 * Slope_066_212 + yint_066_212
    RefSuf047 = RefSuf066 * Slope_047_066 + yint_047_066
    return RefSuf066, RefSuf047

def make_interpolation_cube():
    V = None
    return V

def interpolate(solar_zenith, rel_azimuth, sensor_zenith, cube):
    aot = 0
    
    return aot
    
def invert(refl, angle):
    ndvi_124_212 = NDVI(refl[3], refl[1]) #波段顺序c1100, c212, c138, c124, c086, c066, c055, c047
    ray_AOT047 = 0.1948
    
    ref047 = refl[6]
    ref124 = refl[2]
    ref212 = refl[0]
    solar_zenith = angle[1]
    sensor_zenith = angle[3]
    relative_azimuth = abs(angle[2] - angle[0]) * np.pi / 180
    scatter_angle = math.acos(-math.cos(solar_zenith) * math.cos(sensor_zenith) - 
        math.sin(solar_zenith) * math.sin(sensor_zenith) * math.cos(relative_azimuth))
    

if __name__ == '__main__':
    main()