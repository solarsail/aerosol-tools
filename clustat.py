#!/usr/local/bin/python3

import os
import sys
import clustatlib.cluplot as cluplot
import clustatlib.clustatlib as clustatlib
import clustatlib.clucsv as clucsv

cs = clustatlib.clustat()
legends = []

def main():
    global cs, legends
    os.chdir(sys.path[0])
    ## 读取文件
    print("读取配置文件……")
    # 读取站点列表
    sites = []
    with open('clustatlib/sites.txt') as sitefile:
        for line in sitefile:
            sites.append(line.rstrip())
    # 读取配置文件
    files = []
    header = {}
    with open('clustatlib/config.txt') as conf:
        for line in conf:
            para = line.split(',')
            files.append((para[0], int(para[1])))
            header[int(para[1])] = para[2].rstrip()
    legends = [header[key] for key in sorted(header.keys())]
    # 读取配置文件所指定的数据文件填充数据库，并分配聚类编号
    print("读取文件并填充数据库……")
    for file in files:
        cs.insert_from_file(file[0], file[1])
    #cs.type_stddev()
    #exit()
    ## 生成图片
    print("生成图片……")
    ploter = cluplot.ploter(cs, legends)
    ploter.distribution_img()
    ploter.ssa_img()
    ploter.asy_img()
    ploter.month_percentage_img()
    ploter.year_percentage_img(2001, 2012)
    for site in sites:
        ploter.month_percentage_img(site)
        ploter.year_percentage_img(2001, 2012, site)
    ## 生成统计表
    print("生成统计表……")
    csvb = clucsv.csvbuilder(cs)
    csvb.type_csv()
    csvb.site_type_csv()
    csvb.type_stat_csv()
    csvb.month_type_csv()
    csvb.year_type_csv(2001, 2012)
    for site in sites:
        csvb.month_type_csv(site)
        csvb.year_type_csv(2001, 2012, site)
    
if __name__ == '__main__':
    main()
    print("完成。")
