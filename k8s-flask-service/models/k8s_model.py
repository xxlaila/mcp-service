# -*- coding: utf-8 -*-
"""
@File    : k8s_model.py 
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
from kubernetes import client, config
from .k8s.base import K8sBase
from .k8s.deployment import DeploymentOps
from .k8s.node import NodeOps
from .k8s.pod import PodOps
from .k8s.diagnostics import Diagnostics
from .k8s.utils import PodDiagnostics
from utils.logger import logger

class K8sModel(K8sBase):
    def __init__(self, env='test'):
        super().__init__(env)
        self.load_kube_config()
        self.deployment = DeploymentOps(client.AppsV1Api())
        self.node = NodeOps(self.api)
        self.pod = PodOps(self.api)
        self.diagnostics = Diagnostics(client.ApiClient(), self.api, self)
        self.pod_diagnostics = PodDiagnostics(self.diagnostics, self)

    def load_kube_config(self):
        try:
            config_path = self.get_cluster_auth_info()
            logger.info(f"正在加载kubeconfig文件: {config_path}")
            config.load_kube_config(config_file=str(config_path))
            self.api = client.CoreV1Api()
            logger.info("Kubernetes客户端初始化成功")
        except Exception as e:
            logger.error(f"加载kubeconfig失败: {str(e)}")
            raise

    def execute_method(self, method_name, params):
        """
        执行指定方法并返回结果
        :param method_name: 方法名称
        :param params: 参数字典
        :return: 方法执行结果
        """
        params = self._preprocess_params(method_name, params)
        method = getattr(self, method_name)
        # 特殊处理不需要参数的方法
        if method_name in ['list_all_nodes']:
            return method()
        else:
            return method(params)

    def _preprocess_params(self, func_name, params):
        """
        参数预处理
        :param func_name: 方法名称
        :param params: 原始参数
        :return: 处理后的参数
        """
        if func_name in ['dump_pod_heap_memory', 'dump_pod_cpu', 'check_pods_desc', 'get_pods_last_logs']:
            pod_info = self.get_service_name_by_ip(params)
            if not pod_info:
                raise ValueError("未找到对应Pod")
            params.update(pod_info)

        if func_name in ['scale_deployment']:
            pod_info = self.get_pod_based_on_service(params)
            if not pod_info:
                raise ValueError("未找到服务对应的Pod")
            params.update(pod_info)

        return params

    def __getattr__(self, name):
        """
        动态路由方法调用到对应的子模块
        :param name: 方法名称
        :return: 方法对象
        """
        if name in ['scale_deployment']:
            return getattr(self.deployment, name)
        elif name in ['list_all_nodes', 'describe_node']:
            return getattr(self.node, name)
        elif name in ['get_pods_last_logs', 'get_service_name_by_ip', 'get_pod_based_on_service', 'check_pods_desc']:
            return getattr(self.pod, name)
        elif name in ['dump_pod_cpu', 'dump_pod_heap_memory']:
            return getattr(self.pod_diagnostics, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")