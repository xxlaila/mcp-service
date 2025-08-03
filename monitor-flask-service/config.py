# -*- coding: utf-8 -*-
"""
@File    : config.py 
@Time    : 2025/4/15 19:14
@Author  : xxlaila
@Software: dify
"""
import os
from dotenv import load_dotenv
import logging

load_dotenv()

class Config:
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 6011))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    GRAFANA_URL = os.getenv('grafan_url')
    API_TOKEN = os.getenv('api_token')
    OTHER_PARAS = os.getenv('other_paras', '')