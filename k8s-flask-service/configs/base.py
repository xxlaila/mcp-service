# -*- coding: utf-8 -*-
"""
@File    : base.py 
@Time    : 2025/4/9 10:12
@Author  : xxlaila
@Software: dify
"""
import os
class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')