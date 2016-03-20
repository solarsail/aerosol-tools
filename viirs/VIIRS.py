# -*- coding: utf-8 -*-
"""
Created on Wed Mar 09 22:33:16 2016

@author: 好
"""
import time
import os
import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import aggdraw
from collections import defaultdict
from PIL import Image
from pycoast import ContourWriterAGG
from pyproj import Proj
from pyresample import kd_tree, geometry # 重采样
import json


AOD_MAX = 1.5
VALUE_SCALE = 10000
VALUE_LIMIT = int(AOD_MAX * VALUE_SCALE)


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
    
    
class viirs_file:
    def __init__(self, path):
        
        def scale(data, fill_value = 0):
            data[data >= 65528] = fill_value # 65528或以上为无效点
            data[data > VALUE_LIMIT] = VALUE_LIMIT # 设置 aod 最大值
            data = data.astype(float)
            data /= VALUE_SCALE
            return data
            
        self.path = path
        self.tag = os.path.split(self.path)[1][26:34]
        self.valid = True
        self.aot_550 = None
        self.lat = None
        self.lon = None
        self.swath_def = None

        f = h5py.File(path, 'r')
        geo_dataset = f['/All_Data/VIIRS-Aeros-EDR-GEO_All']
        aero_dataset = f['/All_Data/VIIRS-Aeros-EDR_All']
        aot_550 = aero_dataset['AerosolOpticalDepth_at_550nm'].value
        self.lat = geo_dataset['Latitude'].value
        self.lon = geo_dataset['Longitude'].value
        # 如果数据中没有有效值，或者经纬度有无效值，则将该文件设为无效
        if aot_550.min() >= 65528 or self.lat.min() < -90 or self.lat.max() > 90:
            self.valid = False
        else:
            print("max lat: {}, min lat: {}".format(self.lat.max(), self.lat.min()))
            self.swath_def = geometry.SwathDefinition(lons=self.lon, lats=self.lat)
            self.aot_550 = scale(aot_550)
    
    def locate(self, loc):
        '''
        在数据中查找与指定坐标最接近的坐标点索引，以及该点的坐标值。
        '''
        lat, lon = loc
        dlon = np.square(np.abs(self.lon - lon))
        dlat = np.square(np.abs(self.lat - lat))
        dadd = np.add(dlon,dlat)
        #row=np.argmin(np.min(dadd, axis=1))
        #column=np.argmin(np.min(dadd, axis=0))
        #index = [row, column]
        flat_index = np.argmin(dadd)
        index = np.array(np.unravel_index(flat_index, dadd.shape))
        return index, (self.lon[index], self.lat[index])
        
    def get_area_def(self):
        '''
        获取文件经纬度范围的区域定义。
        '''
        area_def = get_proj_area(lon_min=self.lon.min(), lon_max=self.lon.max(), lat_min=self.lat.min(), lat_max=self.lat.max())
        return area_def
        
    def reproject(self, area_def = None):
        '''
        将文件数据投影到指定区域。默认为数据本身的经纬度范围。
        返回一个掩膜数组，无效值被遮盖。
        '''
        if area_def is None:
            area_def = self.get_area_def()
        result = kd_tree.resample_nearest(self.swath_def, self.aot_550, area_def, radius_of_influence=5000)
        return np.ma.masked_equal(result, 0)


class viirs_file_group:
    def __init__(self, filelist):
        self.files = [viirs_file(name) for name in filelist]
        self.lat_max = max([f.lat.max() for f in self.files if f.valid])
        self.lat_min = min([f.lat.min() for f in self.files if f.valid])
        self.lon_max = max([f.lon.max() for f in self.files if f.valid])
        self.lon_min = min([f.lon.min() for f in self.files if f.valid])

    def get_area_def(self):
        '''
        获取所有文件经纬度范围的外接矩形的区域定义。
        '''
        area_def = get_proj_area(lon_min=self.lon_min, lon_max=self.lon_max, lat_min=self.lat_min, lat_max=self.lat_max)
        return area_def
        
    def reproject(self, area_def = None):
        '''
        将组内所有文件数据投影到指定区域。默认为所有文件经纬度范围的外接矩形。
        返回一个掩膜数组，无效值被遮盖。
        '''
        if area_def is None:
            area_def = self.get_area_def()
            
        masks = []
        # 将每一个AOT填充到大的图像范围内
        for vf in self.files:
            print('{} [{}]'.format(vf.path, 'processing' if vf.valid else 'skipped'))
            if vf.valid:
                result = vf.reproject(area_def)
                masks.append(result)
        # TODO: 空数组检查
        # 将多个图像拼接到一起
        base_mask = masks[0]
        for mask in masks[1:]:
            base_mask[base_mask.mask]=mask[base_mask.mask]
        return base_mask
            
            
def read_conf(filename):
    conf = None
    with open(filename,'r') as config:
        conf = json.load(config)
    return conf


def plotImage(arr) :
    fig  = plt.figure(figsize=(5,5), dpi=80, facecolor='w',edgecolor='w',frameon=True)
    imAx = plt.imshow(arr, origin='lower', interpolation='nearest')
    fig.colorbar(imAx, pad=0.01, fraction=0.1, shrink=1.00, aspect=20)


def plotHistogram(arr) :
    fig = plt.figure(figsize=(5,5), dpi=80, facecolor='w',edgecolor='w',frameon=True)
    plt.hist(arr.flatten(), bins=100)

    
def get_RowColumn_Number(lons,lats,target_lons,target_lats, area_def): 
       
    '''
    已知大图像的经纬度lons、lats，需要裁剪的图像的范围target_lons,target_lats
    求需要裁剪的图像的行数从row1到row2，已知列数从column1到column2
    '''
    target_column,target_row=[0,0]
    row,column=area_def.shape
    target_column[0]=np.uint8(column*(target_lons[0]-lons[0])/lons[1]-lons[0])
    target_column[1]=np.uint8(column*(target_lons[1]-lons[0])/lons[1]-lons[0])
    target_row[0]=np.uint8(row*(target_lats[0]-lats[0])/lats[1]-lats[0])
    target_row[1]=np.uint8(row*(target_lats[1]-lats[0])/lats[1]-lats[0])
    
    return target_column,target_row

def read_files(path):
    filenames = os.listdir(path)
    input_path=[]
    out_path=[]
    out_path.append([])
    for i in xrange(len(filenames)):
        input_path.append(os.path.join(path,filenames[i]))
    j=0
    date=filenames[0].split('_',5)[2]
    file_split=[]
    file_split.append([])
    file_split[j].append(date)
    out_path[j].append(input_path[0])
    length=len(filenames)
    for i in xrange(1,length):
        filename=filenames[i].split('_',5)[2]
        if filename==file_split[j][0]:
            file_split[j].append(filename)
            out_path[j].append(input_path[i])
        else:
            j=j+1
            file_split.append([])
            file_split[j].append(filename)
            out_path.append([])
            out_path[j].append(input_path[i])
    return out_path


def group_files(path):
    filenames = [name for name in os.listdir(path) if name.endswith('.h5')]
    d = defaultdict(list)
    for name in filenames:
        d[name[17:25]].append(os.path.join(path, name))
    return d
    
    
def draw_colorbar(image):    
    font_size = 16
    tick_pen = aggdraw.Pen('black', 1.0)
    border_pen = aggdraw.Pen('white', 1.0)
    font = aggdraw.Font('white', r"c:\windows\fonts\times.ttf", size=font_size)
    
    figure_size = (image.size[0] + 150, image.size[1] + 50)
    figure = Image.new('RGB', figure_size)
    
    legend = Image.new('RGB', (100, 350))
    
    xorg = 20
    yorg = 25
    bar = np.linspace(1, 0, 300)
    bar = bar.reshape(300, 1).repeat(20, 1)
    bar_data = np.uint8(cm.jet(bar) * 255)
    bar_img = Image.fromarray(bar_data)

    tick = np.linspace(AOD_MAX, 0, 11)

    legend.paste(bar_img, (xorg, yorg, bar_img.size[0]+xorg, bar_img.size[1]+yorg))
    draw = aggdraw.Draw(legend)
    for t in tick:
        y = (AOD_MAX - t) * 300 / AOD_MAX
        draw.line((15+xorg,y+yorg-0.5, 20+xorg,y+yorg-0.5), tick_pen) # 为显示清晰的刻度线，需要绘制在半像素坐标上
        draw.text((25+xorg, y+yorg-font_size/2), str(t), font)
    draw.flush()
    
    image_boundary = (25, 25, 25+image.size[0], 25+image.size[1])
    figure.paste(image, image_boundary)
    legend_x = 30 + image.size[0]
    legend_y = (figure.size[1]-legend.size[1]) / 2
    figure.paste(legend, (legend_x, legend_y, legend_x+legend.size[0], legend_y+legend.size[1]))
    draw = aggdraw.Draw(figure)
    draw.rectangle(image_boundary, border_pen)
    draw.flush()
    
    return figure
    
    
def save_img(img_data, area_def, shp_path, path, suffix):
    #plotImage(img_data)
    img_data = np.uint8(cm.jet(img_data / AOD_MAX) * 255)
    img = Image.fromarray(img_data)
    cw = ContourWriterAGG(shp_path)
    cw.add_coastlines(img, area_def, resolution='l', width=1.0, level=2) # 分辨率 {'c', 'l', 'i', 'h', 'f'}
    font = aggdraw.Font('white', r"c:\windows\fonts\times.ttf", size=16) # Times New Roman 字体
    cw.add_grid(img, area_def, (10.0,10.0),(2.0,2.0), font, width=1.0, outline='white', outline_opacity=175,
                 minor_outline='gray', minor_outline_opacity=200, minor_width=0.5, minor_is_tick=False)
    figure = draw_colorbar(img)
    filename = ''.join(("result", suffix, ".png"))
    figure.save(os.path.join(path, filename),'PNG')
    
    
def main():  
    start = time.clock()
    conf = read_conf(r'D:\mei\VIIRS\config.txt')
    beijing_loc = conf['beijing'] #北京站的经纬度
    
    '''
    读取HDF5文件，按日期输出叠加图像
    '''  
    data_path = conf['data_path']
    shape_file_path = conf['shape_file_path']
    img_output_path = conf['img_output_path']
    #outpath=read_files(folder_path)
    name_lists = group_files(data_path)
    for datestr in name_lists:
        name_list = name_lists[datestr]
        group = viirs_file_group(name_list)
        result = group.reproject()
        save_img(result, group.get_area_def(), shape_file_path, img_output_path, datestr)
#        for f in group.files:
#            result = f.reproject()
#            save_img(result, f.get_area_def(), r'D:\mei', datestr + f.tag)

    '''
    获取图像经纬度范围,几何校正
    '''
    #area_def = get_proj_area(zone=54, lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max)
    #result = kd_tree.resample_nearest(swath_def, AOT_550, area_def, radius_of_influence=5000)
        
    #locate =Virrs_File.locate(beijing_loc)#找北京站点对应的行列号
    #index=locate[0]
    #beijing_aot=AOT_550[index[0],index[1]]
    
    
    '''
    图像裁剪
    '''
    #target_column,target_row=get_RowColumn_Number(lons,lats,target_lons,target_lats, area_def)
    #result_slice=result[target_row[0]:target_row[1],target_column[0]:target_column[1]]    
    
    #result=result*255
    
    #result = np.uint8(result * 255)
    #plotImage(result)
    #img = Image.fromarray(result, 'L')
    #coast_dir=r'E:\ModisData'
    #cw = ContourWriterAGG(coast_dir)
    #cw.add_coastlines(img, area_def, resolution='i', width=0.5)
    #save_path=r'E:\result.png'
    #img.save(save_path,'PNG')
    end = time.clock()
    #f.close()
    print(end - start)

if __name__ == '__main__':
    main()
