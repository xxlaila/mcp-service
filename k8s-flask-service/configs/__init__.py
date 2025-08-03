# -*- coding: utf-8 -*-
"""
@File    : __init__.py.py 
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """基础配置"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    LOG_LEVEL = 'INFO'

    # K8s配置
    KUBE_CONFIG_DIR = os.getenv('KUBE_CONFIG_DIR', '/etc/kube')
    POD_LOG_PATH = os.getenv('POD_LOG_PATH', '/var/log/k8s')
    LOCAL_LOG_PATH = os.getenv('LOCAL_LOG_PATH', '/tmp/k8s-logs')

    # 环境配置
    ENVIRONMENTS = os.getenv('environments', '{}')
