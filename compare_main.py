# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 23:39:38 2016

@author: 欣晔
"""
import numpy as np

from matplotlib import cm
from operator import and_
from aerosol_tools import config, projection, image, satellite_data as sd


def main():
    conf = config.ConfigFile(r'd:\mei\viirs\config.txt')
    beijing_loc = conf.beijing #北京站的经纬度
    
    # 如何处理损坏的文件
    bad_modis_handler = sd.LogHandler(conf.err_file, halt=True)
    bad_viirs_handler = sd.LogHandler(conf.err_file, halt=False)
    sd.ModisData.bad_file_handler = bad_modis_handler
    sd.ViirsData.bad_file_handler = bad_viirs_handler
    
    '''
    读取HDF5文件，按日期输出叠加图像
    '''  
    #outpath=read_files(folder_path)
    viirs_name_lists = sd.group_files(conf.viirs_path, 'viirs')
    modis_name_lists = sd.group_files(conf.modis_path, 'modis')


    '''    
    输出modis文件名，检查modis文件是否能够打开，打不开写在error_file里
    '''
#    for datestr in modis_name_lists: # 以 modis 为准
#        print(datestr)
#        modis_name_list = modis_name_lists[datestr]
#        viirs_name_list = viirs_name_lists[datestr]
#        viirs_group = sd.DataGroup(viirs_name_list, sd.ViirsData, conf.max_aod)
#        modis_group = sd.DataGroup(modis_name_list, sd.ModisData, conf.max_aod)
#        
#    # 如果存在有问题的文件则退出
#    with open(conf.err_file, 'r') as ef:
#        lines = ef.readlines()
#        if len(lines) > 0:
#            print(lines)
#            exit(1)
    '''       
    跳过之前已经处理了的文件 
    '''       
    with open(conf.processed_file, 'r') as pf:
        skipped = pf.read()
        
    pf = open(conf.processed_file, 'a')
    '''
    处理一个月的VIIRS数据
    '''
    diff_area_def = projection.get_proj_area(lon_min=72, lon_max=136, lat_min=16, lat_max=55) #中国的经纬度范围
    
    modis_counts = np.ones(diff_area_def.shape)
    viirs_counts = np.ones(diff_area_def.shape)
    diffs_counts = np.ones(diff_area_def.shape)
    modis_month_mean = np.ma.masked_all(diff_area_def.shape)
    viirs_month_mean = np.ma.masked_all(diff_area_def.shape)
    diffs_month_mean = np.ma.masked_all(diff_area_def.shape)
    
    for datestr in modis_name_lists:
        print(datestr)
        if datestr in skipped:
            continue
        
        modis_name_list = modis_name_lists[datestr]
        viirs_name_list = viirs_name_lists[datestr]
        
        viirs_group = sd.DataGroup(viirs_name_list, sd.ViirsData, conf.max_aod)
        modis_group = sd.DataGroup(modis_name_list, sd.ModisData, conf.max_aod)
        
        modis_result = projection.group_reproject(modis_group, diff_area_def)
        viirs_result = projection.group_reproject(viirs_group, diff_area_def)
        diffs = modis_result - viirs_result

        modis_month_mean = np.ma.array(viirs_month_mean.data + modis_result.data,
                                       mask=map(and_, viirs_month_mean.mask, modis_result.mask))
        viirs_month_mean = np.ma.array(viirs_month_mean.data + viirs_result.data,
                                       mask=map(and_, viirs_month_mean.mask, viirs_result.mask))
        diffs_month_mean = np.ma.array(diffs_month_mean.data + diffs.data,
                                       mask=map(and_, diffs_month_mean.mask, diffs.mask))
        modis_counts[~modis_result.mask] += 1
        viirs_counts[~viirs_result.mask] += 1
        diffs_counts[~diffs.mask] += 1

        sd.save_merged(modis_result, viirs_result, diffs, conf.img_output_path, datestr)
        
        np.clip(diffs, -0.2, 0.2, out=diffs)
        np.clip(diffs_month_mean, -0.2, 0.2, out=diffs_month_mean)
        modis_pref = {'aod_max': conf.max_aod, 'aod_min': 0, 'step': 0.1}
        diff_pref = {'aod_max': 0.2, 'aod_min': -0.2, 'step': 0.1}
        image.save(modis_result, modis_pref, cm.rainbow, diff_area_def, conf.shape_file_path, conf.img_output_path, datestr + 'modis')
        image.save(viirs_result, modis_pref, cm.rainbow, diff_area_def, conf.shape_file_path, conf.img_output_path, datestr + 'viirs')
        image.save(diffs, diff_pref, cm.Spectral_r, diff_area_def, conf.shape_file_path, conf.img_output_path, datestr)
        pf.write(''.join([datestr, '\n']))
        
    modis_month_mean /= modis_counts
    viirs_month_mean /= viirs_counts
    diffs_month_mean /= diffs_counts
    
    sd.save_merged(modis_month_mean, viirs_month_mean, diffs_month_mean, conf.img_output_path,'monthly-mean-')
    image.save(modis_month_mean, modis_pref, cm.rainbow, diff_area_def, conf.shape_file_path, conf.img_output_path, 'modis-month-mean')
    image.save(viirs_month_mean, modis_pref, cm.rainbow, diff_area_def, conf.shape_file_path, conf.img_output_path, 'viirs-month-mean')
    image.save(diffs_month_mean, diff_pref, cm.Spectral_r, diff_area_def, conf.shape_file_path, conf.img_output_path, 'diffs-month-mean')    
    
    pf.close()


if __name__ == '__main__':
    main()