import sqlite3
import pystaggrelite3
from dateutil import parser

class clustat:
    def query(self, sql):
        self.__cursor.execute(sql)
        return self.__cursor.fetchall()

    def __init__(self):
        '''对象自动初始化'''
        # 在内存中建立数据库，不同的clustat对象会打开各自独立的数据库
        self.__sqlite_conn = sqlite3.connect(':memory:')
        self.__cursor = self.__sqlite_conn.cursor()
        self.__sqlite_conn.create_aggregate("stdev", 1, pystaggrelite3.stdev)
        # 创建数据表
        self.__cursor.execute('DROP TABLE IF EXISTS records')
        self.__cursor.execute('''CREATE TABLE records
            (site TEXT, dt TEXT, cluster INTEGER,
            refr440 REAL, refr675 REAL, refr870 REAL, refr1020 REAL,
            refi440 REAL, refi675 REAL, refi870 REAL, refi1020 REAL,
            volmedianradf REAL, stddevf REAL, volconf REAL,
            volmedianradc REAL, stddevc REAL, volconc REAL,
            ssa440 REAL, ssa675 REAL, ssa870 REAL, ssa1020 REAL,
            asy440 REAL, asy675 REAL, asy870 REAL, asy1020 REAL,
            skyerror REAL, sphericity REAL,
            aot1020 REAL, aot870 REAL, aot675 REAL, aot440 REAL,
            water REAL)''')
        #self.__cursor.execute('DROP TABLE IF EXISTS mh')
        #self.__cursor.execute('''CREATE TABLE mh (month TEXT)''')
        #for m in range(1, 13):
        #    self.__cursor.execute("INSERT INTO mh VALUES ('%02d')" % m)

    def __del__(self):
        # 关闭数据库
        self.__sqlite_conn.close()

    def insert_from_file(self, filename, clusterno):
        '''
        将文件中所有数据的站点、日期时间和给定的聚类编号导入数据库
        filename: 文件名
        clusterno: 聚类编号
        '''
        with open(filename) as datafile:
            # 忽略第一行
            line = datafile.readline()
             # 读文件的每行
            for line in datafile:
                fields = line.split(',')
                # 将站点、时间（由日期和时间组合）和聚类编号拼成VALUES参数
                dt = "%s %s" % (fields[1], fields[2])
                # 将日期转换为标准格式 YYYY-mm-DDTHH:MM:SS
                head = "'%s','%s',%d" % (fields[0], parser.parse(dt).isoformat(), clusterno)
                data = [fields[i] for i in range(3, 32)]
                value = "(%s)" % ",".join((head, ",".join(data)))
                #print(value)
                # 插入数据
                self.__cursor.execute("INSERT INTO records VALUES %s" % value)
        # 提交事务
        self.__sqlite_conn.commit()

    def month_type_stat(self, site = None):
        '''12个月各类别总数与所占百分比'''
        if site != None:
            where = "WHERE site = '%s'" % site
        else:
            where = ""
        # 如果统计天数则使用 COUNT(DISTINCT DATE(dt))
        self.__cursor.execute("DROP VIEW IF EXISTS monthpercentage")
        self.__cursor.execute('''
        CREATE VIEW monthpercentage AS
        SELECT cluster, strftime('%m', dt) AS month, COUNT(*) AS count
        FROM records {0}
        GROUP BY cluster, month
        '''.format(where))
        self.__cursor.execute('''
        SELECT a.cluster, a.month, a.count, (a.count*100.0)/b.total AS percentage
        FROM (monthpercentage AS a JOIN (SELECT month, SUM(count) AS total
                FROM monthpercentage
                GROUP BY month) b
        ON a.month = b.month)''')
        all = self.__cursor.fetchall()
        #return all
        index = 0
        v = []
        p = []
        #print("SQL result length: %d" % len(all))
        while index < len(all):
            values = []
            percents = []
            for m in range(1, 13):
                if index == len(all):
                    values.append(0)
                    percents.append(0)
                    continue
                row = all[index]
                #print("index: %d, rec month: %s, month: %d" % (index, row[1], m))
                if m == int(row[1]):
                    values.append(row[2])
                    percents.append(row[3])
                    index += 1
                else:
                    values.append(0)
                    percents.append(0)
            v.append(values)
            p.append(percents)
        return v, p

    def year_type_stat(self, start_year, end_year, site = None):
        '''每年各类别总数与所占百分比'''
        if site != None:
            where = "WHERE site = '%s'" % site
        else:
            where = ""
        # 如果统计天数则使用 COUNT(DISTINCT DATE(dt))
        self.__cursor.execute("DROP VIEW IF EXISTS yearpercentage")
        self.__cursor.execute('''
        CREATE VIEW yearpercentage AS
        SELECT cluster, strftime('%Y', dt) AS year, COUNT(*) AS count
        FROM records {0}
        GROUP BY cluster, year
        '''.format(where))
        self.__cursor.execute('''
        SELECT a.cluster, a.year, a.count, (a.count*100.0)/b.total AS percentage
        FROM (yearpercentage AS a JOIN (SELECT year, SUM(count) AS total
                FROM yearpercentage
                GROUP BY year) b
        ON a.year = b.year)''')
        all = self.__cursor.fetchall()

        index = 0
        v = []
        p = []
        #print("SQL result length: %d" % len(all))
        while index < len(all):
            values = []
            percents = []
            for y in range(start_year, end_year+1):
                # 数据已到结尾，但尚未到结束年
                if index == len(all):
                    values.append(0)
                    percents.append(0)
                    continue
                #print("index: %d, rec year: %s, year: %d" % (index, all[index][1], y))
                # 数据早于开始年
                while int(all[index][1]) < start_year:
                    index += 1
                    #print("earlier")
                    #print("index: %d, rec year: %s, year: %d" % (index, all[index][1], y))
                # 正常匹配
                row = all[index]
                if y == int(row[1]):
                    values.append(row[2])
                    percents.append(row[3])
                    index += 1
                else:   # 数据空缺
                    values.append(0)
                    percents.append(0)
            # 数据晚于结束年
            while index < len(all) and int(all[index][1]) > end_year:
                index += 1
            v.append(values)
            p.append(percents)
            #print(p)
        return v, p

    def type_stat(self):
        '''各类别总数与所占百分比'''
        self.__cursor.execute('''
        SELECT cluster, COUNT(*), (COUNT(*)*100.0)/(SELECT COUNT(*) FROM records)
        FROM records
        GROUP BY cluster''')
        all = self.__cursor.fetchall()
        return all

    def site_type_stat(self):
        '''每个站点各类别总数与所占百分比'''
        self.__cursor.execute("DROP VIEW IF EXISTS sitetype")
        self.__cursor.execute('''
        CREATE VIEW sitetype AS
        SELECT site, cluster, COUNT(*) as count FROM records
        GROUP BY site, cluster''')
        self.__cursor.execute('''
        SELECT a.site, a.cluster, a.count, (a.count*100.0)/b.total AS percentage
        FROM (sitetype AS a JOIN (SELECT site, SUM(count) AS total
                FROM sitetype
                GROUP BY site) b
        ON a.site = b.site)''')
        all = self.__cursor.fetchall()
        self.__cursor.execute("SELECT COUNT(DISTINCT cluster) FROM records")
        types = self.__cursor.fetchone()[0]

        index = 0
        l = []
        while index < len(all):
            site = all[index][0]
            row = [site,]
            for t in range(1, types+1):
                if index == len(all):
                    row.append(0) # count
                    row.append(0) # percentage
                    continue
                if t == all[index][1]:
                    row.append(all[index][2]) # count
                    row.append(all[index][3]) # percentage
                    index += 1
                else:
                    row.append(0) # count
                    row.append(0) # percentage
            l.append(row)
        return l, types

    def type_means(self):
        self.__cursor.execute('''
        SELECT cluster,
                AVG(refr440), AVG(refr675), AVG(refr870), AVG(refr1020),
                AVG(refi440), AVG(refi675), AVG(refi870), AVG(refi1020),
                AVG(volmedianradf), AVG(stddevf), AVG(volconf),
                AVG(volmedianradc), AVG(stddevc), AVG(volconc),
                AVG(ssa440), AVG(ssa675), AVG(ssa870), AVG(ssa1020),
                AVG(asy440), AVG(asy675), AVG(asy870), AVG(asy1020),
                AVG(aot440), AVG(aot675), AVG(aot870), AVG(aot1020),
                AVG(skyerror), AVG(sphericity), AVG(water)
        FROM records
        GROUP BY cluster''')
        all = self.__cursor.fetchall()
        return all

    def type_stddev(self):
        self.__cursor.execute('''
        SELECT cluster,
                STDEV(refr440), STDEV(refr675), STDEV(refr870), STDEV(refr1020),
                STDEV(refi440), STDEV(refi675), STDEV(refi870), STDEV(refi1020),
                STDEV(volmedianradf), STDEV(stddevf), STDEV(volconf),
                STDEV(volmedianradc), STDEV(stddevc), STDEV(volconc),
                STDEV(ssa440), STDEV(ssa675), STDEV(ssa870), STDEV(ssa1020),
                STDEV(asy440), STDEV(asy675), STDEV(asy870), STDEV(asy1020),
                STDEV(aot440), STDEV(aot675), STDEV(aot870), STDEV(aot1020),
                STDEV(skyerror), STDEV(sphericity), STDEV(water)
        FROM records
        GROUP BY cluster''')
        all = self.__cursor.fetchall()
        return all
