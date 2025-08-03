# -*- coding: utf-8 -*-
"""
@File    : base.py 
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
import os
import json
from pathlib import Path

class K8sBase:
    def __init__(self, env='test'):
        self.cluster = ''
        self.pod_log_path = os.getenv('pod_log_path')
        self.down_log_url = os.getenv('down_log_url')
        self.local_log_path = os.getenv('local_log_path')
        self.jdk_path = os.getenv('jdk_path')
        self.flame_graph_path = os.getenv('flame_graph_path')
        self._load_env_config(env)

    def _load_env_config(self, env):
        raw_env = os.getenv('environments', '{}')
        env_dict = json.loads(raw_env)
        config = env_dict.get(env, {})

        if not config:
            raise ValueError(f"未找到 {env} 环境配置")

        self.cluster = config.get('cluster_name', '')
        if not self.cluster:
            raise ValueError(f"{env} 环境缺少 cluster_name 配置")

        return config

    def get_cluster_auth_info(self):
        config_path = Path(__file__).parent.parent.parent / 'kube' / f'{self.cluster}'
        if not config_path.exists():
            raise FileNotFoundError(f"Kube配置文件未找到: {config_path}")
        return str(config_path)