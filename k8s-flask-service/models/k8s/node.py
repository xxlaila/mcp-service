# -*- coding: utf-8 -*-
"""
@File    : node.py.py 
@Time    : 2025/4/8 12:03
@Author  : xxlaila
@Software: dify
"""
from kubernetes.client.exceptions import ApiException
from utils.logger import logger

class NodeOps:
    def __init__(self, core_api):
        self.api = core_api

    def list_all_nodes(self):
        logger.info("获取节点信息")
        try:
            nodes = self.api.list_node(timeout_seconds=30)
            logger.info(f"获取节点信息成功: {nodes.items}")
            formatted_nodes = [self._format_node_info(node) for node in nodes.items]
            return {"nodes": formatted_nodes}
        except ApiException as e:
            logger.error(f"Kubernetes API 异常: {e}")
            raise RuntimeError(f"Kubernetes API 错误: {e}") from e
        except Exception as e:
            logger.error(f"获取节点信息异常: {str(e)}")
            raise RuntimeError(f"获取节点信息异常: {str(e)}") from e

    def _format_node_info(self, node):
        return {
            # 基础信息
            "name": node.metadata.name,
            "creation_time": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else "N/A",

            # 核心状态
            "ready_status": next(
                (status.status for status in node.status.conditions if status.type == "Ready"), "Unknown"
            ),
            "conditions": {
                condition.type: {
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message if condition.message else None
                }
                for condition in node.status.conditions
            },

            # 资源容量
            "capacity": {
                "cpu": node.status.capacity.get("cpu", "N/A"),
                "memory": node.status.capacity.get("memory", "N/A"),
                "pods": node.status.capacity.get("pods", "N/A"),
                "storage": node.status.capacity.get("ephemeral-storage", "N/A")
            },

            # 可分配资源
            "allocatable": {
                "cpu": node.status.allocatable.get("cpu", "N/A"),
                "memory": node.status.allocatable.get("memory", "N/A"),
                "pods": node.status.allocatable.get("pods", "N/A"),
                "storage": node.status.allocatable.get("ephemeral-storage", "N/A")
            },

            # 网络信息
            "internal_ip": next(
                (addr.address for addr in node.status.addresses if addr.type == "InternalIP"), "N/A"
            ),
            "pod_cidr": node.spec.pod_cidr if node.spec else "N/A",

            # 调度相关
            "unschedulable": getattr(node.spec, "unschedulable", False),
            "scale_down_protected": node.metadata.annotations.get(
                "cluster-autoscaler.kubernetes.io/scale-down-disabled") == "true",

            # 标签/注解（精选重要字段）
            "labels": {
                k: v for k, v in node.metadata.labels.items()
                if k in {"app1", "deploy", "failure-domain.beta.kubernetes.io/region"}
            } if node.metadata.labels else None,

            # 异常检测标志
            "has_issues": any(
                condition.status != "False"
                for condition in node.status.conditions
                if condition.type in {"MemoryPressure", "DiskPressure", "PIDPressure"}
            )
        }

    def describe_node(self, params):
        logger.info(f"获取节点信息: {params}")
        try:
            node_info = self.api.read_node(name=params.get('pod'))
            return self._extract_node_issues(node_info)
        except ApiException:
            return None

    def _extract_node_issues(self, node_info):
        if not node_info or not node_info.status or not node_info.status.conditions:
            return {"issues": ["无法获取节点状态"]}

        issues = []
        node_status = {
            "name": node_info.metadata.name,
            "uid": node_info.metadata.uid,
            "phase": node_info.status.phase,
            "conditions": []
        }
        for condition in node_info.status.conditions:
            condition_info = {
                "type": condition.type,
                "status": condition.status,
                "reason": condition.reason,
                "message": condition.message,
                "last_transition_time": condition.last_transition_time.isoformat()
            }
            node_status["conditions"].append(condition_info)
            if condition.status == "False" and condition.type != "Ready":
                issues.append(condition_info)

        return {
            "node_status": node_status,
            "issues": issues if issues else ["没有检测到异常"]
        }