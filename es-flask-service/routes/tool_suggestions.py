# -*- coding: utf-8 -*-
"""
@File    : tool_suggestions.py 
@Time    : 2025/4/15 10:58
@Author  : xxlaila
@Software: dify
"""
from typing import Dict, List

def generate_tool_suggestions() -> List[Dict]:
    """
    返回固定的工具调用模板样例，供用户参考。
    """
    suggestions = []

    # 基础节点监控指标
    suggestions.append({
        "name": "command",
        "parameters": {
            "cluster_name": "<your_cluster_name>",
            "action": "_nodes/stats?v&h=nodes.*.name,nodes.*.jvm.mem.heap_used_percent,nodes.*.os.cpu.percent,nodes.*.thread_pool.search.active&format=json"
        },
        "reason": "采集节点的CPU、内存、线程池使用率"
    })
    # 集群整体状态
    suggestions.append({
        "name": "command",
        "parameters": {
            "cluster_name": "<your_cluster_name>",
            "action": "_cluster/stats?v&h=indices.count,status,nodes.count&format=json"
        },
        "reason": "获取集群健康状态和索引总数"
    })
    # 线程池拒绝情况
    suggestions.append({
        "name": "command",
        "parameters": {
            "cluster_name": "<your_cluster_name>",
            "action": "_cat/thread_pool/search?v&h=host,name,active,rejected&format=json"
        },
        "reason": "分析是否存在线程池任务排队或拒绝"
    })

    return suggestions
