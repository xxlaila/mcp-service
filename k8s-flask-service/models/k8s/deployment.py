# -*- coding: utf-8 -*-
"""
@File    : deployment.py 
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
from kubernetes.client import AppsV1Api
from kubernetes.client.exceptions import ApiException

class DeploymentOps:
    def __init__(self, api_client):
        self.api = AppsV1Api(api_client)

    def scale_deployment(self, params):
        try:
            current_deployment = self.api.read_namespaced_deployment(
                name=params['container'],
                namespace=params['namespace']
            )
            current_replicas = current_deployment.spec.replicas
            target_replicas = int(params['replicas'])

            if current_replicas == target_replicas:
                return f"Deployment {params['deployment']} 已经是 {target_replicas} 副本"

            current_deployment.spec.replicas = target_replicas
            self.api.patch_namespaced_deployment(
                name=current_deployment.metadata.name,
                namespace=params['namespace'],
                body=current_deployment
            )

            return {
                "status": "success",
                "message": f"已从 {current_replicas} 扩容至 {target_replicas}",
                "deployment": params['deployment'],
                "namespace": params['namespace'],
                "current_replicas": current_replicas,
                "target_replicas": target_replicas
            }
        except ApiException as e:
            return {
                "status": "error",
                "message": f"API错误: {str(e)}"
            }