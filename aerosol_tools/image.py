# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 23:32:08 2016

@author: 欣晔
"""
import os
import aggdraw
import numpy as np

from PIL import Image
from pycoast import ContourWriterAGG


def draw_colorbar(image, img_pref, pattern):
    aod_min = img_pref['aod_min']
    aod_max = img_pref['aod_max']
    step = img_pref['step']
    ticks = int(round((aod_max - aod_min) / step + 1))
    #print('max: {}, min: {}, step: {}, ticks: {}'.format(aod_max, aod_min, step, ticks))

    font_size = 30
    tick_pen = aggdraw.Pen('black', 1.0)
    border_pen = aggdraw.Pen('black', 1.0)
    font = aggdraw.Font('black', r"c:\windows\fonts\times.ttf", size=font_size)
    
    figure_size = (image.size[0] + 150, image.size[1] + 50)
    figure = Image.new('RGB', figure_size, color=(255,255,255))
    
    xorg = 20
    yorg = 25
    bar_height = 600
    bar_width = 40
    legend = Image.new('RGB', (bar_width+100, bar_height+50), color=(255,255,255))
    bar = np.linspace(1, 0, bar_height+1)
    bar = bar.reshape(bar_height+1, 1).repeat(bar_width, 1)
    bar_data = np.uint8(pattern(bar) * 255)
    bar_img = Image.fromarray(bar_data)

    tick = np.linspace(aod_max, aod_min, ticks)

    legend.paste(bar_img, (xorg, yorg-1, bar_img.size[0]+xorg, bar_img.size[1]+yorg-1))
    draw = aggdraw.Draw(legend)
    for t in tick:
        y = (aod_max - t) * bar_height / (aod_max - aod_min)
        draw.line((bar_width+xorg-10, y+yorg-0.5, bar_width+xorg,y+yorg-0.5), tick_pen) # 为显示清晰的刻度线，需要绘制在半像素坐标上
        draw.text((bar_width+xorg+5, y+yorg-2-font_size/2), str(t), font)
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
    
    
def save(img_data, img_pref, pattern, area_def, shp_path, path, suffix):
    """将数据保存为图像。"""
    #plotImage(img_data)
    aod_min = img_pref['aod_min']
    aod_max = img_pref['aod_max']
    size = img_data.shape[::-1] # (行,列) -> (长,宽)
    img_data = np.uint8(pattern((img_data - aod_min) / (aod_max - aod_min)) * 255)
    img = Image.new(mode='RGBA', size=size, color=(255,255,255,255))
    src = Image.fromarray(img_data, 'RGBA')
    img.paste(src, (0,0), src)
    cw = ContourWriterAGG(shp_path)
    #cw.add_coastlines(img, area_def, resolution='l', width=1, level=1, outline='gray') # 分辨率 {'c', 'l', 'i', 'h', 'f'}
    #cw.add_borders(img, area_def, resolution='l', width=1.0, level=3, outline='black')
    cw.add_shapefile_shapes(img, area_def, filename=os.path.join(shp_path, 'ChinaProvince.shp'), width=1.0, outline='black')
    font = aggdraw.Font('black', r"c:\windows\fonts\times.ttf", size=30) # Times New Roman 字体
    cw.add_grid(img, area_def, (10.0,10.0),(2.0,2.0), font, width=1.0, outline='black', outline_opacity=175,
                 minor_outline='gray', minor_outline_opacity=200, minor_width=0.5, minor_is_tick=False)
    figure = draw_colorbar(img, img_pref, pattern)
    filename = ''.join(("result", suffix, ".png"))
    figure.save(os.path.join(path, filename),'PNG')