# -*- coding: utf-8 -*-
"""
Created on Fri Feb 26 10:30:01 2016

@author: mei
"""
from __future__ import print_function
import os
import sqlite3
import textwrap
import math
import subprocess
import numpy as np
import time
import json

devnull = open(os.devnull, 'w')

def read_conf(filename):
    conf = None
    with open(filename) as config:
        conf = json.load(config)
    return conf
        
def rayleigh_od(devwave, height):
    '''
    功能： 计算rayleigh光学厚度（此程序不再使用该函数，而直接使用modis_rayleigh_od） 
    原理：从大气层外开始往地面方向逐渐增加, 即height = 0 时的光学厚度最大
    因此要计算某个高度的光学厚度时，需要计算两遍(height=0， height=real height)
    然后相减即可。高度的单位为米
    devwave: 波长，微米
    height:  高度，米
    '''
    p0 = 1013.25
    Ht = 8430.0
    pressure = p0 * math.exp(-1.0 * height / Ht)
    rayexp = -1.0 * (3.9164 + 0.074 * devwave + 0.05 / devwave)
    raytau = 0.00865 * math.pow(devwave, rayexp)
    rod = pressure / 1013.25 * raytau
    return rod


class LUT:
    def __init__(self, path):
        self.path = path
        self.dbfile = os.path.join(self.path, 'lut.db')
        self.conn = sqlite3.connect(self.dbfile)
        
    def close(self):
        self.conn.close()
        
    def table(self, wavelength):
        return 'wavelength_%s' % int(wavelength * 1000)
        
    def create_schema(self, wavelength):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS %s
                     (type INTEGER, aod REAL, solar REAL, rel REAL, 
                      sensor REAL, scat REAL, FT REAL, s REAL, ref REAL)''' % self.table(wavelength))
        self.conn.commit()
        
    def table_size(self, wavelength):
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) FROM %s' % self.table(wavelength))
        result = c.fetchone()[0]
        return result
	
    def select_record(self, wavelength, solar, rel, sensor):
        query = 'SELECT type, aod, scat, FT, s, ref FROM %s where solar=? and rel=? and sensor=?' % self.table(wavelength)
        c = self.conn.cursor()
        c.execute(query, solar, rel, sensor)
        result = c.fecthall()
        return result
        
    def select_parameter(self, wavelength, param):
        query = 'SELECT DISTINCT {0} FROM {1} ORDER BY {0} ASC'.format(param, self.table(wavelength))
        c = self.conn.cursor()
        c.execute(query)
        result = c.fecthall()
        return result
        
    def insert(self, aod, tag, zenith, wavelength, rt3_data):
        '''
        向查找表中插入数据。
        aod: 气溶胶光学厚度
        tag: 气溶胶类型标签
        zenith: 太阳天顶角
        wavelength: 波长，微米
        rt3_data: rt3执行结果，由RT3.run()获得
        '''
        def t_s(ref_aerosol, ref_total_1, ref_total_2):
            FT = 6 * (ref_total_1 - ref_aerosol) * (ref_total_2 - ref_aerosol) / (ref_total_2 - ref_total_1);
            s = 4 - 6 * (ref_total_1 - ref_aerosol) / (ref_total_2 - ref_total_1);
            return FT, s
            
        c = self.conn.cursor()
        rows = []
        for value_0, value_1, value_25 in zip(rt3_data[0], rt3_data[1], rt3_data[2]):
            rel = value_0[1]
            sensor = value_0[2]
            scat = value_0[3]
            ref = value_0[4]
            t, s = t_s(value_0[4], value_1[4], value_25[4])
            row = [tag, aod, zenith, rel, sensor, scat, t, s, ref]
            rows.append(row)
        c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?)' % self.table(wavelength), rows)
        self.conn.commit()
        
    
class Mie:
    def __init__(self, exe_path):
        self.path = exe_path
        self.exe = os.path.join(self.path, 'mie318.exe')
        self.input = os.path.join(self.path, 'input_MIE_D.txt')
        
    def make_mie_input(self, wavelength, distribution, refractive, tag = None):
        '''
        生成米散射的输入
        '''
        params = {
            'wl': wavelength,
            'ref0': refractive[0],
            'ref1': refractive[1],
            'dist0': distribution[1],
            'dist1': distribution[2],
            'dist2': distribution[0],
            'dist3': distribution[4],
            'dist4': distribution[5],
            'dist5': distribution[3],
        }
        params['out'] = 'mie_%s_%s.sca' % (wavelength, tag) if tag else 'mie_%s.sca' % wavelength
        input_mie_content = textwrap.dedent(
        '''
        %(wl)s
        n
        (%(ref0)s,%(ref1)s)
        0.05 15
        184
        600
        %(dist0)s %(dist1)s %(dist2)s %(dist3)s %(dist4)s %(dist5)s
        %(out)s
        ''' % params).strip()
    
        return input_mie_content

    def run(self, wavelength, distribution, refractive, tag = None):
        input_str = self.make_mie_input(wavelength, distribution, refractive, tag)
        with open (self.input, 'w') as mie_file:
            mie_file.write(input_str)
        sp = subprocess.Popen(self.exe, cwd=self.path, stdout=devnull)
        sp.communicate()
        

class RT3:
    def __init__(self, exe_path):
        self.path = exe_path
        self.exe = os.path.join(self.path, 'rt3.exe')
        self.input = os.path.join(self.path, 'input.txt')
        self.layer = os.path.join(self.path, 'layer.txt')
        self.output = os.path.join(self.path, 'rt3.%s')
    
    def make_layer_input(self, aod, wavelength, tag = None):                            
        '''
        生成瑞利散射输入
        '''
        # ATBD中的RayleighOD参考值
        modis_rayleigh_od = {
            '0.44': 0.1948,
            '0.676': 0.052,
            '2.12': 0.0004
        }
        #ray_aod = rayleigh_od(wavelength, 0) - rayleigh_od(wavelength, 705000)
        ray_aod = modis_rayleigh_od[str(wavelength)]
        top_aod = aod + ray_aod;
        params = {
            'TopAOD': top_aod,
            'AOD': aod
        }
        params['mie'] = 'mie_%s_%s.sca' % (wavelength, tag) if tag else 'mie_%s.sca' % wavelength
        
        layers_content = textwrap.dedent(
        '''
        %(TopAOD)s 0.0 0.0 'rayleigh.sca'
        %(AOD)s 0.0 0.0 '%(mie)s'
        0.0 0.0 0.0 ' '
        ''' % params).strip()
        
        return layers_content
    
    def make_rt3_input(self, zenith, wavelength, tag = None):
        '''
        生成RT3的三个输入,计算F、T、S
        地表分别设为0/0.1/0.25
        '''
        params = {
            'z': zenith,
            'ref': 0.0,
            'w': wavelength
        }
        refs = [0.0, 0.1, 0.25]
        input_str = textwrap.dedent(
        '''
        1
        50
        G
        4
        layer.txt
        N
        1
        3.1415
        %(z)s
        0.0
        L
        %(ref)s
        0.0
        %(w)s
        W
        IQ
        1
        1
        90
        %(out)s
        '''
        ).strip()
        
        input_content = []
        for ref in refs:
            params['ref'] = ref
            params['out'] = 'rt3.%s' % ref
            input_content.append(input_str % params)
    
        return input_content
    
    def read_output(self, ref):
        data = []
        with open(self.output % ref) as result:
            for line in result:
                values = [float(value) for value in line.strip().split()]
                data.append(values)
        return data
        
    def run(self, aod, zenith, wavelength, tag = None):
        results = []
        layer_str = self.make_layer_input(aod, wavelength, tag)
        with open (self.layer, 'w') as layer_file:
            layer_file.write(layer_str)
        inputs = self.make_rt3_input(zenith, wavelength, tag)
        sps = []
        for input_str in inputs:
            with open (self.input, 'w') as input_file:
                input_file.write(input_str)
            sps.append(subprocess.Popen(self.exe, cwd=self.path, stdout=devnull))
            time.sleep(0.2)
        refs = [0.0, 0.1, 0.25]
        for sp, ref in zip(sps, refs):
            sp.communicate()
            result = self.read_output(ref)
            results.append(result)
        return results
    
    
def start_point(count, tag_count, aod_count, zenith_count):
    if count == tag_count * aod_count * zenith_count:
        return True, 0, 0, 0

    tag_start = count / (aod_count * zenith_count)
    count -= tag_start * (aod_count * zenith_count)
    aod_start = count / zenith_count
    count -= aod_start * zenith_count
    zenith_start = count
    return False, tag_start, aod_start, zenith_start
	
	
def main():
    '''
    连接数据库，构建查找表,查找表里的内容：wavelength，SolarZenith，SensorZenith，RelativeAzimuth，ScatterAngle，AOD,Reflectance,FT,S
    定义气溶胶类型参数：refractive， distribution
    '''
    conf = read_conf("config.txt")
    refractive = [
        [[1.413,-0.007],[1.426,-0.005],[1.432,-0.005]], # 对应non-absorbing型气溶胶在440nm，676nm，1020nm四个波段
        [[1.462,-0.014],[1.481,-0.01],[1.491,-0.01]],   # 对应moderate-absorbing型气溶胶的refractive index
        [[1.471,-0.025],[1.487,-0.02],[1.502,-0.022]],  # high absorbing型
        [[1.494,-0.008],[1.521,-0.004],[1.519,-0.004]]  # Coarse型
    ]
    distribution = [
        [0.127,0.219,0.51,0.08,2.731,0.602],   # 对应non-absorbing型气溶胶的谱分布
        [0.103,0.183,0.498,0.112,2.673,0.625], # 对应moderate-absorbing型气溶胶的谱分布
        [0.084,0.179,0.516,0.083,2.757,0.643], # high absorbing型
        [0.083,0.161,0.515,0.3,2.402,0.599]    # Coarse型
    ]
    
    wavelengths = conf['wavelengths']
    tags = conf['tags']
    
    #path = r'D:\mei\lut'
    binpath = conf['bin-path']
    lutpath = conf['lut-path']
    mie = Mie(binpath)
    rt3 = RT3(binpath)
    lut = LUT(lutpath)
    
    start = time.clock()
    count = 0
    for i in range(len(wavelengths)): # 波长
        wavelength = wavelengths[i]
        lut.create_schema(wavelength)
        table_size = lut.table_size(wavelength)
        # 计算本次运行的起始位置，以跳过数据库中已经填充的内容。
        # 必须保证与之前运行的参数完全相同，否则数据库中的内容会前后不一致。
        table_size /= 4500 # 每个循环4500行，在rt3输入中定义
        count += table_size
        print('skipped {} loops'.format(table_size))
        skip, tag_start, aod_start, zenith_start = start_point(table_size, len(tags), 21, 11)
        if skip:
            continue

        for tag, ref, dist in zip(tags, refractive, distribution): # 四种气溶胶类型
            if tag_start > 0:
                tag_start -= 1
                continue
            mie.run(wavelength, dist, ref[i], tag) # 每种气溶胶执行一次mie
            for AOD in np.linspace(aod_start * 0.1, 2.0, 21 - aod_start):  # 光学厚度从0到2，21为取样数
                for zenith in xrange(zenith_start * 6, 65, 6): # 太阳天顶角，从0到65，6为步长，共11个
                    result = rt3.run(AOD, zenith, wavelength, tag) # 每个光学厚度、天顶角执行一次rt3
                    lut.insert(AOD, tag, zenith, wavelength, result) # 插入数据库
                    count += 1
                    print('{}/{}, {}-{}-{}-{}'.format(
                        count, len(wavelengths) * len(tags) * 21 * 11,
                        wavelength, tag, AOD, zenith))
                zenith_start = 0
            aod_start = 0
            
                    
    lut.close()
    end = time.clock()
    total = end - start
    print('All done. Total time: {}'.format(total))
    
if __name__ == '__main__':
    main()

