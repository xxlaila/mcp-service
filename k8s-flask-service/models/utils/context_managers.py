# -*- coding: utf-8 -*-
"""
@File    : context_managers.py 
@Time    : 2025/4/10 10:35
@Author  : xxlaila
@Software: dify
"""
from contextlib import contextmanager
from utils.logger import logger

@contextmanager
def k8s_command_execution(name):
    """管理K8s命令执行的上下文"""
    logger.info(f"开始执行K8s命令: {name}")
    try:
        yield
        logger.info(f"K8s命令 {name} 执行成功")
    except Exception as e:
        logger.error(f"K8s命令 {name} 执行失败: {str(e)}")
        raise