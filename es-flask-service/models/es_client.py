# -*- coding: utf-8 -*-
"""
@File    : es_client.py 
@Time    : 2025/4/2 16:50
@Author  : xxlaila
@Software: dify
"""

from elasticsearch import Elasticsearch
from config.es_config import get_cluster_config

class ESClient:
    @staticmethod
    def get_client(cluster_name: str) -> Elasticsearch:
        try:
            return Elasticsearch(**get_cluster_config(cluster_name))
        except Exception as e:
            raise RuntimeError(f"ES connection failed: {str(e)}")

class ESHttpClient:
    @staticmethod
    def get_client(cluster_name: str) -> Elasticsearch:
        try:
            config = get_cluster_config(cluster_name)
            # 添加验证配置
            print(config)
            es = Elasticsearch(
                **config,
                verify_certs=False,

            )
            # 测试连接
            try:
                if not es.ping():
                    raise RuntimeError("无法连接到Elasticsearch集群")
            except Exception as e:
                raise RuntimeError(f"无法连接到Elasticsearch集群: {str(e)}")
            return es
        except Exception as e:
            raise RuntimeError(f"ES连接失败: {str(e)}")