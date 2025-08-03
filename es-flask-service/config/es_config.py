# -*- coding: utf-8 -*-
"""
@File    : es_config.py 
@Time    : 2025/4/2 16:50
@Author  : xxlaila
@Software: dify
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_cluster_config(cluster_name: str) -> dict:
    clusters = json.loads(os.getenv("CLUSTERS_CONFIG"))
    config = clusters.get(cluster_name)

    if not config:
        raise ValueError(f"Cluster {cluster_name} not configured")
    if not config.get("endpoint"):
        raise ValueError(f"Invalid config for cluster {cluster_name}: Missing endpoint")

    cluster_config = {
        "hosts": [config["endpoint"]],
        "timeout": config.get("timeout", 30)
    }

    username = config.get("username")
    password = config.get("password")
    if username and password:
        cluster_config["http_auth"] = (username, password)

    return cluster_config