# -*- coding: utf-8 -*-
"""
@File    : query_controller.py
@Time    : 2025/4/2 16:51
@Author  : xxlaila
@Software: dify
"""
from models.es_client import ESClient

def execute_query(cluster_name: str, dsl: dict) -> dict:

    try:
        es = ESClient.get_client(cluster_name)
        response = es.search(**dsl)
        print(f"response: {response}")
        return {
            "status": "success",
            "data": response
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }