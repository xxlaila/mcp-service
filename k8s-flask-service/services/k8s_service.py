# -*- coding: utf-8 -*-
"""
@File    : k8s_service.py
@Time    : 2025/3/17 11:52
@Author  : xxlaila
@Software: dify
"""
import logging
import json
from kubernetes.client.exceptions import ApiException
from models.k8s_model import K8sModel


class K8sService:
    def handle_request(self, request):
        content = request.get_data(as_text=True)
        try:
            data = json.loads(content)
            logging.info(f"Request body: {data}")

            if not data:
                return {"error": "Request body must be JSON"}, 400

            env = data.get('env')
            func_name = data.get('func_name')

            if not all([env, func_name]):
                return {"error": "缺少必要参数 env 或 func_name"}, 400

            k8s_helper = K8sModel(env=env)
            params = data

            # 处理不同功能请求
            if func_name in ['dump_pod_heap_memory', 'dump_pod_cpu', 'check_pods_desc', 'get_pods_last_logs']:
                pod_info = k8s_helper.get_service_name_by_ip(data)
                if not pod_info:
                    return {"error": "未找到Pod"}, 404
                params.update(pod_info)

            result = getattr(k8s_helper, func_name)(params)
            return {"result": result}, 200

        except ApiException as e:
            logging.error(f"Kubernetes API错误: {str(e)}")
            return {"error": f"Kubernetes API错误: {str(e)}"}, 500
        except Exception as e:
            logging.error(f"处理请求异常: {str(e)}")
            return {"error": f"服务器内部错误: {str(e)}"}, 500
