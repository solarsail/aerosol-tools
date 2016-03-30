# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 23:34:42 2016

@author: 欣晔
"""
import json
    
class ConfigFile(object):
    def __init__(self, filename):
        with open(filename) as cf:
            self.conf = json.load(cf)

    def __getattr__(self, name):
        return self.conf[name]

