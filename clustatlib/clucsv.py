import numpy as np
import os
import os.path

class csvbuilder:
    def __init__(self, cs):
        self.cs = cs
        if not os.path.isdir('csv'):
            os.mkdir('csv')
        
    def month_type_csv(self, site = None):
        label = 'all' if site == None else site
        values, percentages = self.cs.month_type_stat(site)
        header = ",".join(["type{},%".format(t) for t in range(1, len(values)+1)])
        header = "month," + header
        all = []
        for i in range(len(values)):
            all.append(values[i])
            all.append(percentages[i])
        mat = np.matrix(all)
        mat = mat.transpose().tolist()
        content = []
        for i in range(12):
            content.append("%d,%s" % (i+1, ','.join([str(field) for field in mat[i]])))
        content = '\n'.join(content)
        with open("csv/month_type_%s.csv" % label, 'w') as outfile:
            outfile.write('\n'.join((header, content)))
        
    def year_type_csv(self, start_year, end_year, site = None):
        label = 'all' if site == None else site
        values, percentages = self.cs.year_type_stat(start_year, end_year, site)
        header = ",".join(["type{},%".format(t) for t in range(1, len(values)+1)])
        header = "year," + header
        all = []
        for i in range(len(values)):
            all.append(values[i])
            all.append(percentages[i])
        mat = np.matrix(all)
        mat = mat.transpose().tolist()
        content = []
        for i in range(start_year, end_year+1):
            content.append("%d,%s" % (i, ','.join([str(field) for field in mat[i-start_year]])))
        content = '\n'.join(content)
        with open("csv/year_type_%s.csv" % label, 'w') as outfile:
            outfile.write('\n'.join((header, content)))
        
    def type_csv(self):
        header = "type,count,percentage%"
        all = self.cs.type_stat()
        content = '\n'.join([','.join([str(field) for field in row]) for row in all])
        with open("csv/type_count.csv", 'w') as outfile:
            outfile.write('\n'.join((header, content)))
        
    def site_type_csv(self):
        all, types = self.cs.site_type_stat()
        header = ",".join(["type{},%".format(t) for t in range(1, types+1)])
        header = "site," + header
        content = '\n'.join([','.join([str(field) for field in row]) for row in all])
        with open("csv/site_type_count.csv", 'w') as outfile:
            outfile.write('\n'.join((header, content)))
        
    def type_stat_csv(self):
        header = "type,refr440,refr675,refr870,refr1020,refi440,refi675,refi870,refi1020,volmedianradf,stddevf,volconf,volmedianradc,stddevc,volconc,ssa440,ssa675,ssa870,ssa1020,asy440,asy675,asy870,asy1020,aot440,aot675,aot870,aot1020,skyerror,sphericity,water"
        list1 = self.cs.type_means()
        list2 = self.cs.type_stddev()
        l = []
        for i in range(len(list1)):
            l.append(list1[i])
            stddevline = list(list2[i])
            stddevline[0] = "stddev"
            l.append(stddevline)
        content = '\n'.join([','.join([str(field) for field in row]) for row in l])
        with open("csv/type_stat.csv", 'w') as outfile:
            outfile.write('\n'.join((header, content)))
        