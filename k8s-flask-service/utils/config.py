# -*- coding: utf-8 -*-
"""
@File    : config.py 
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
import os
from dotenv import load_dotenv

def load_config():
    load_dotenv()
    return {
        'pod_log_path': os.getenv('pod_log_path'),
        'down_log_url': os.getenv('down_log_url'),
        'local_log_path': os.getenv('local_log_path'),
        'jdk_path': os.getenv('jdk_path'),
        'flame_graph_path': os.getenv('flame_graph_path'),
        'environments': os.getenv('environments')
    }
