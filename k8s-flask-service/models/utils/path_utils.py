# -*- coding: utf-8 -*-
"""
@File    : path_utils.py 
@Time    : 2025/4/10 10:35
@Author  : xxlaila
@Software: dify
"""

class PodPathUtils:
    @staticmethod
    def get_pod_log_path(config, pod_name, container, filename=None):
        """生成Pod日志路径"""
        base = f"{config.pod_log_path}/{container}/log"
        return f"{base}/{filename}" if filename else base

    @staticmethod
    def get_report_url(config, date_dir, pod_name, filename=None):
        """生成报告URL"""
        base = f"{config.down_log_url}/reports/{date_dir}/{pod_name}"
        return f"{base}/{filename}" if filename else base