# -*- coding: utf-8 -*-
"""
@File    : pod.py 
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
import re
from  utils.logger import logger
from kubernetes.client.exceptions import ApiException
from kubernetes import client

class PodOps:

    def __init__(self, core_api):
        self.api = core_api

    def get_pods_last_logs(self, params):
        logger.info(f"开始查询Pod日志: {params}")
        try:
            raw_logs = self.api.read_namespaced_pod_log(
                namespace=params.get('namespace'),
                name=params.get('pod'),
                tail_lines=1000,
                container=params.get('container'),
            )
            if not raw_logs:
                return {"logs": "没有可用的日志"}

            # 处理日志
            caused_by_blocks = []
            current_block = []

            for line in raw_logs.splitlines():
                if "Caused by" in line:
                    if current_block:  # 保存前一个块(最多15行)
                        caused_by_blocks.append("\n".join(current_block[:15]))
                    current_block = [line]  # 开始新块
                elif current_block:  # 只在当前有活跃块时收集
                    current_block.append(line)

            # 添加最后一个块
            if current_block:
                caused_by_blocks.append("\n".join(current_block[:15]))

            # 返回结果
            result_logs = "\n\n--------\n".join(caused_by_blocks) if caused_by_blocks else raw_logs
            return {"logs": result_logs}

        except client.ApiException as e:
            error_msg = f"查询Pod日志失败: {str(e)}"
            if e.status == 404:
                error_msg = f"Pod或容器不存在: {params['pod']}/{params['container']}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            logger.error(f"获取日志时发生意外错误: {str(e)}")
            raise RuntimeError(f"获取日志失败: {str(e)}") from e

    def get_service_name_by_ip(self, query_data):
        logger.info(f"开始查询Pod信息: {query_data}")
        target_pod = query_data.get('pod', '').strip()
        if not target_pod:
            return None

        is_ip = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target_pod)
        field_selector = f"status.podIP={target_pod}" if is_ip else f"metadata.name={target_pod}"

        try:
            pods = self.api.list_pod_for_all_namespaces(field_selector=field_selector, timeout_seconds=30)
        except ApiException as e:
            logger.error(f"查询Pod信息时发生异常: {e}")
            return {"msg": "查询Pod信息时发生异常"}

        if not pods:
            logger.error(f"查询不到IP或者Pod: {target_pod}")
            return {"msg": "没有查询到Pod或IP"}

        for pod in pods.items:
            if (is_ip and pod.status.pod_ip == target_pod) or \
                    (not is_ip and pod.metadata.name == target_pod):
                return {
                    "namespace": pod.metadata.namespace,
                    "pod": pod.metadata.name,
                    "container": pod.spec.containers[0].name,
                    "pod_ip": pod.status.pod_ip,
                    "node": pod.spec.node_name,
                    "staus": pod.status.phase,
                    "node_ip": pod.status.host_ip,
                    "image": pod.spec.containers[0].image,
                    "create_time": pod.metadata.creation_timestamp.isoformat(),
                    "resource": {
                        "limits": pod.spec.containers[0].resources.limits,
                        'requests': pod.spec.containers[0].resources.requests
                    }
                }

        logger.error(f"未找到匹配的Pod: {target_pod}")
        return {"msg": "未找到匹配的Pod"}

    def get_pod_based_on_service(self, query_data):
        service = query_data.get('pod', '').strip()
        if not service:
            return None

        label_selector = f"app={service}"
        pods = self.api.list_pod_for_all_namespaces(label_selector=label_selector, timeout_seconds=30)
        if not pods.items:
            return None

        pod_info = []
        for pod in pods.items:
            pod_info.append([
                pod.metadata.name,
                pod.status.pod_ip,
                pod.status.phase,
                pod.status.host_ip,
                pod.spec.node_name,
                pod.spec.containers[0].image,
                pod.metadata.creation_timestamp.isoformat()
            ])

        return {
            "namespace": pods.items[0].metadata.namespace,
            "container": pods.items[0].spec.containers[0].name,
            "resources": {
                "limits": pods.items[0].spec.containers[0].resources.limits,
                'requests': pods.items[0].spec.containers[0].resources.requests
            },
            "pod_info": pod_info
        }

    def check_pods_desc(self, params):
        params = params
        try:
            pod_obj = self.api.read_namespaced_pod(
                namespace=params.get('namespace'),
                name=params.get('pod')
            )
            events = self.api.list_namespaced_event(
                namespace=params.get('namespace'),
                field_selector=f"involvedObject.name={pod_obj.metadata.name}",
                timeout_seconds=30
            )
            logger.info(f"开始查询Pod事件: {events}")

            event_messages = "\n".join(e.message for e in events.items if e.message) if events.items else ""

            # 返回包含原始参数和事件信息的结果
            result = {
                "events": event_messages,
            }
            logger.info(f"方法执行结果: {result}")
            return result
        except client.ApiException as e:
            logger.error(f"Kubernetes API 异常: {e}")
            if e.status == 404:
                raise ValueError(f"未找到Pod: {params['pod']}") from e
            raise RuntimeError(f"Kubernetes API 错误: {e}") from e
        except Exception as e:
            logger.error(f"检查Pod描述时发生意外错误: {str(e)}")
            raise RuntimeError(f"检查Pod描述失败: {str(e)}") from e