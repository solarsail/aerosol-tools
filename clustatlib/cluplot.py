import matplotlib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import AutoMinorLocator
import numpy as np
import os

class ploter:
    def __init__(self, cs, legends):
        self.cs = cs
        self.legends = legends
        if not os.path.isdir('img'):
            os.mkdir('img')
        with open("clustatlib/range.txt", "r") as rangefile:
            for line in rangefile:
                fields = line.split(":")
                if fields[0] == "distribution":
                    self.distr_range = (float(fields[1]), float(fields[2]))
                elif fields[0] == "ssa":
                    self.ssa_range = (float(fields[1]), float(fields[2]))
                elif fields[0] == "asy":
                    self.asy_range = (float(fields[1]), float(fields[2]))
                    
    def month_percentage_img(self, site = None):
        values, percentages = self.cs.month_type_stat(site)
        label = 'China' if site == None else site
        ## 参数设置
        months = 12
        bar_width = 0.15 # 柱宽度
        # 柱颜色
        colors = ('r', 'b', 'orange', 'm', 'c')
        # 坐标轴字体设置
        font = {'family' : 'serif',
                'serif'  : 'Times New Roman',
                'size'   : 12}
        matplotlib.rc('font', **font)
        # 图例字体设置
        fontP = FontProperties(size = 12)
        # 设置图尺寸，必须在绘制图像之前设置
        plt.figure(num=2, figsize=(12, 3.5), dpi=80, facecolor='w', edgecolor='k')
        plt.clf()
        # 设置坐标轴刻度
        plt.tick_params(axis='both', which='both', # 控制所有4个轴和主副刻度
            direction='out', # 刻度指向外侧
            bottom='on', top='off', left='on', right='off') # 隐藏上方和右方的刻度
        # 右上方标题
        plt.text(11.5, 80, label, fontdict={'fontsize':16}, ha = 'right')
        ## 绘图
        rects = []
        index = np.arange(months)
        bars = len(percentages)
        for i in range(bars):
            plt.bar(index + bar_width * i, percentages[i], bar_width, color = colors[i], label = self.legends[i])
        
        plt.xlabel('Month')
        plt.ylabel('Percentage (%)')
        plt.axis([-bar_width, 12, 0,100])
        plt.xticks(index + bars * bar_width / 2, [str(month) for month in range(1,13)])
        l = plt.legend(loc = 2, ncol = bars, prop = fontP)
        l.draw_frame(False)
        plt.tight_layout()
        plt.savefig("img/%s_month.png" % label, format = 'png')
        
    def year_percentage_img(self, start_year, end_year, site = None):
        values, percentages = self.cs.year_type_stat(start_year, end_year, site)
        label = 'China' if site == None else site
        ## 参数设置
        years = end_year - start_year + 1
        bar_width = 0.15 # 柱宽度
        # 柱颜色
        colors = ('r', 'b', 'orange', 'm', 'c')
        # 坐标轴字体设置
        font = {'family' : 'serif',
                'serif'  : 'Times New Roman',
                'size'   : 12}
        matplotlib.rc('font', **font)
        # 图例字体设置
        fontP = FontProperties(size = 12)
        # 设置图尺寸，必须在绘制图像之前设置
        plt.figure(num=2, figsize=(12, 3.5), dpi=80, facecolor='w', edgecolor='k')
        plt.clf()
        # 设置坐标轴刻度
        plt.tick_params(axis='both', which='both', # 控制所有4个轴和主副刻度
            direction='out', # 刻度指向外侧
            bottom='on', top='off', left='on', right='off') # 隐藏上方和右方的刻度
        # 右上方标题
        plt.text(11.5, 80, label, fontdict={'fontsize':16}, ha = 'right')
        ## 绘图
        rects = []
        index = np.arange(years)
        bars = len(percentages)
        for i in range(bars):
            plt.bar(index + bar_width * i, percentages[i], bar_width, color = colors[i], label = self.legends[i])
        
        plt.xlabel('Year')
        plt.ylabel('Percentage (%)')
        plt.axis([-bar_width, 12, 0,100])
        plt.xticks(index + bars * bar_width / 2, [str(year) for year in range(start_year, end_year+1)])
        l = plt.legend(loc = 2, ncol = bars, prop = fontP)
        l.draw_frame(False)
        plt.tight_layout()
        plt.savefig("img/%s_year.png" % label, format = 'png')
        
    def distribution_img(self):
        means = self.cs.type_means()
        # 线颜色
        colors = ('r', 'b', 'orange', 'm', 'c')
        # 坐标轴字体设置
        font = {'family' : 'serif',
                'serif'  : 'Times New Roman',
                'size'   : 12}
        matplotlib.rc('font', **font)
        #matplotlib.rc('text', usetex=True)
        # 图例字体设置
        fontP = FontProperties(size = 12)
        # 设置图尺寸，必须在绘制图像之前设置
        plt.figure(num=1, figsize=(6, 5), dpi=80, facecolor='w', edgecolor='k')
        plt.clf()
        # 设置坐标轴刻度
        plt.tick_params(axis='both', which='both', # 控制所有4个轴和主副刻度
            direction='out', # 刻度指向外侧
            bottom='on', top='off', left='on', right='off') # 隐藏上方和右方的刻度
        plt.axis([0.01, 20, self.distr_range[0], self.distr_range[1]])
        #plt.yticks(np.arange(0, 0.5, 0.1))
        plt.axes().yaxis.set_minor_locator(AutoMinorLocator(2))
        ## 绘图
        x = np.arange(0.01, 20.0 + 0.01, 0.01)
        for i in range(len(means)):
            mean = means[i]
            C_f = mean[11]; sigma_f = mean[10]; r_mf = mean[9]
            C_c = mean[14]; sigma_c = mean[13]; r_mc = mean[12]
            #print("C_f:%f sigma_f:%f r_mf:%f C_c:%f sigma_c:%f r_mc:%f" % (C_f, sigma_f, r_mf, C_c, sigma_c, r_mc))
            y = C_f / np.sqrt(2*np.pi) / sigma_f * np.exp(-pow(np.log(x) - np.log(r_mf), 2) / pow(np.log(sigma_f), 2) / 2) + C_c / np.sqrt(2*np.pi) / sigma_c * np.exp(-pow(np.log(x) - np.log(r_mc), 2) / pow(np.log(sigma_c), 2) / 2)
            plt.semilogx(x, y, colors[i], label = self.legends[i])
        plt.xlabel("Radius ($\mu$m)")
        plt.ylabel("dV/dlnr ($\mu$m$^3/\mu$m$^2$)")
        l = plt.legend(loc = 2, prop = fontP)
        l.draw_frame(False)
        plt.tight_layout()
        plt.savefig("img/distribution.png", format = 'png')
        
    def ssa_img(self):
        means = self.cs.type_means()
        stddevs = self.cs.type_stddev()
        # 线颜色
        colors = ('r', 'b', 'orange', 'm', 'c')
        # 坐标轴字体设置
        font = {'family' : 'serif',
                'serif'  : 'Times New Roman',
                'size'   : 12}
        matplotlib.rc('font', **font)
        # 图例字体设置
        fontP = FontProperties(size = 12)
        # 设置图尺寸，必须在绘制图像之前设置
        plt.figure(num=1, figsize=(6, 5), dpi=80, facecolor='w', edgecolor='k')
        plt.clf()
        # 设置坐标轴刻度
        plt.tick_params(axis='both', which='both', # 控制所有4个轴和主副刻度
            direction='out', # 刻度指向外侧
            bottom='on', top='off', left='on', right='off') # 隐藏上方和右方的刻度
        plt.axis([400, 1100, self.ssa_range[0], self.ssa_range[1]])
        ## 绘图
        x = [440, 675, 870, 1020]
        for i in range(len(means)):
            mean = means[i]
            stddev = stddevs[i]
            ssa440 = mean[15]; ssa675 = mean[16]; ssa870 = mean[17]; ssa1020 = mean[18];
            sd440 = stddev[15]; sd675 = stddev[16]; sd870 = stddev[17]; sd1020 = stddev[18];
            y = [ssa440, ssa675, ssa870, ssa1020]
            error = [sd440, sd675, sd870, sd1020]
            plt.errorbar(x, y, yerr=error, fmt='-o', color=colors[i])
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Single Scattering Albedo")
        #l = plt.legend(loc = 2, prop = fontP)
        #l.draw_frame(False)
        plt.tight_layout()
        plt.savefig("img/ssa.png", format = 'png')
        
    def asy_img(self):
        means = self.cs.type_means()
        stddevs = self.cs.type_stddev()
        # 线颜色
        colors = ('r', 'b', 'orange', 'm', 'c')
        # 坐标轴字体设置
        font = {'family' : 'serif',
                'serif'  : 'Times New Roman',
                'size'   : 12}
        matplotlib.rc('font', **font)
        # 图例字体设置
        fontP = FontProperties(size = 12)
        # 设置图尺寸，必须在绘制图像之前设置
        plt.figure(num=1, figsize=(6, 5), dpi=80, facecolor='w', edgecolor='k')
        plt.clf()
        # 设置坐标轴刻度
        plt.tick_params(axis='both', which='both', # 控制所有4个轴和主副刻度
            direction='out', # 刻度指向外侧
            bottom='on', top='off', left='on', right='off') # 隐藏上方和右方的刻度
        plt.axis([400, 1100, self.asy_range[0], self.asy_range[1]])
        ## 绘图
        x = [440, 675, 870, 1020]
        for i in range(len(means)):
            mean = means[i]
            stddev = stddevs[i]
            asy440 = mean[19]; asy675 = mean[20]; asy870 = mean[21]; asy1020 = mean[22];
            sd440 = stddev[19]; sd675 = stddev[20]; sd870 = stddev[21]; sd1020 = stddev[22];
            y = [asy440, asy675, asy870, asy1020]
            error = [sd440, sd675, sd870, sd1020]
            plt.errorbar(x, y, yerr=error, fmt='-o', color=colors[i])
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Asymmertry Parameter")
        #l = plt.legend(loc = 2, prop = fontP)
        #l.draw_frame(False)
        plt.tight_layout()
        plt.savefig("img/asy.png", format = 'png')
