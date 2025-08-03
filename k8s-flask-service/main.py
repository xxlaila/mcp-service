# -*- coding: utf-8 -*-
"""
@File    : main.py 
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
from flask import Flask, request, send_from_directory
import time
import subprocess
import os, re, json
import ast
from dotenv import load_dotenv
import logging
from pathlib import Path
from kubernetes import client, config
from kubernetes.client import CoreV1Api
from kubernetes.client.exceptions import ApiException
from kubernetes.stream import stream
from datetime import datetime
import subprocess

app = Flask(__name__)

logger = logging.getLogger(__name__)
date_dir = datetime.now().strftime("%Y%m%d")

class K8sHelper:
    def __init__(self, env='test'):
        self.pod = ''
        self.api = None
        self.service = None
        self.container = None
        self.cpu_local_path = None
        self.heap_path = None
        self.log_path = None

        load_dotenv()
        self._load_env_config(env)

    def _load_env_config(self, env):
        """解析.env中的字典结构配置"""
        try:
            # 读取原始环境变量
            raw_env = os.getenv('environments', '{}')

            # 将字符串转换为Python字典
            env_dict = json.loads(raw_env)

            # 获取指定环境的配置
            config = env_dict.get(env, {})

            if not config:
                raise ValueError(f"未找到 {env} 环境配置")

            # 设置实例属性
            self.cluster = config.get('cluster_name', '')
            self.pod_log_path = os.getenv('pod_log_path')
            self.down_log_url = os.getenv('down_log_url')
            self.local_log_path = os.getenv('local_log_path')
            self.jdk_path = os.getenv('jdk_path')
            self.flame_graph_path = os.getenv('flame_graph_path')

            if not self.cluster:
                raise ValueError(f"{env} 环境缺少 cluster_name 配置")

            return config

        except SyntaxError:
            raise ValueError("环境变量格式错误，请检查environments配置格式")

    def get_cluster_auth_info(self):
        """
        获取 kube 配置文件路径
        :return:
        """
        """获取kube配置文件路径"""
        config_path = Path(__file__).parent / 'kube' / f'{self.cluster}'

        if not config_path.exists():
            error_msg = f"Kube配置文件未找到: {config_path}"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)
        return str(config_path)

    def load_kube_config(self):
        """
        加载 kube 配置文件
        :return:
        """
        config_path = self.get_cluster_auth_info()
        config.load_kube_config(config_file=str(config_path))
        logging.info(f"Load kube config file: {config_path}")
        self.api = client.CoreV1Api()

    def scale_deployment(self, params):
        """
        扩容Deployment
        :param params: 包含namespace和deployment名称的字典
            - namespace: 命名空间
            - deployment: Deployment名称
            - replicas: 扩容数量
        :return:
        """
        if not self.api:
            self.load_kube_config()

        try:
            apps_v1 = client.AppsV1Api()
            current_deployment = apps_v1.read_namespaced_deployment(
                name=params['container'],
                namespace=params['namespace']
            )
            current_replicas = current_deployment.spec.replicas
            target_replicas = int(params['replicas'])
            if current_replicas == target_replicas:
                logging.info(f"Deployment {params['deployment']} 已经是 {target_replicas} 副本")
                return f"Deployment {params['deployment']} 已经是 {target_replicas} 副本"

            current_deployment.spec.replicas = target_replicas
            apps_v1.patch_namespaced_deployment(
                name=current_deployment.metadata.name,
                namespace=params['namespace'],
                body=current_deployment
                )
            logging.info(f"Deployment {params['deployment']} 扩容到 {target_replicas} 副本")
            return {
                "status": "success",
                "message": f"已从 {current_replicas} 扩容至 {target_replicas}",
                "deployment": params['deployment'],
                "namespace": params['namespace'],
                "current_replicas": current_replicas,
                "target_replicas": target_replicas
            }
        except ApiException as e:
            logging.error(f"扩容Deployment失败: {e}")
            return {
                "status": "error",
                "message": f"API错误: {str(e)}"
            }
        except Exception as e:
            logging.error(f"扩容异常: {e}")
            return {
                "status": "error",
                "message": f"扩容异常: {str(e)}"
            }

    def get_pods_last_logs(self, params):
        """
        获取Pod最后100行日志
        :param params: 包含namespace和pod名称的字典
        :return: 最后100行日志内容
        """
        if not self.api:
            self.load_kube_config()

        try:
            logs = self.api.read_namespaced_pod_log(
                namespace=params.get('namespace'),
                name=params.get('pod'),
                tail_lines=100,
                container=params.get('container'),
            )
            return logs
        except ApiException as e:
            logging.error(f"获取Pod日志失败: {e}")
            return None

    def list_all_nodes(self):
        """
        获取集群所有节点信息
        :return: 节点列表，包含名称、状态等信息
        """
        if not self.api:
            self.load_kube_config()

        try:
            nodes = self.api.list_node(timeout_seconds=30)
            return [
                {
                    # 基础信息
                    "name": node.metadata.name,
                    "uid": node.metadata.uid,
                    "provider_id": node.spec.provider_id if node.spec else "N/A",
                    "creation_time": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else "N/A",

                    # 核心状态
                    "ready_status": next(
                        (status.status for status in node.status.conditions
                         if status.type == "Ready"), "Unknown"
                    ),
                    "conditions": {
                        condition.type: {
                            "status": condition.status,
                            "reason": condition.reason,
                            # "message": condition.message[:100] + "..." if condition.message else None  # 截断长消息
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
                        (addr.address for addr in node.status.addresses
                         if addr.type == "InternalIP"), "N/A"
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
                for node in nodes.items
            ]
        except ApiException as e:
            logging.error(f"获取节点列表失败: {e}")
            return None

    def describe_node(self, params):
        """
        获取节点详细信息
        :param node_name: 节点名称
        :return: 节点详细信息，格式如下：
        """
        if not self.api:
            self.load_kube_config()

        try:
            node_info = self.api.read_node(name=params.get('node_name'))
            return self.extract_node_issues(node_info)
        except ApiException as e:
            logging.error(f"获取节点详细信息失败: {e}")
            return None

    def extract_node_issues(self, node_info):
        """从 Node 信息中提取可能的异常"""
        issues = []

        if not node_info or not node_info.status or not node_info.status.conditions:
            return ["无法获取节点状态"]

        for condition in node_info.status.conditions:
            if condition.status == "True" and condition.type == "Ready":
                continue  # 节点健康，不需要记录
            if condition.status == "False":  # 可能的异常情况
                issues.append({
                    "type": condition.type,
                    "reason": condition.reason,
                    "message": condition.message,
                    "last_transition_time": condition.last_transition_time
                })

        return issues if issues else ["没有检测到异常"]

    def get_pod_based_on_service(self, query_data):
        """
        通过服务名查询 Pod 完整信息
        :return: 返回与服务关联的 Pod 信息，格式如下：
        {
            "namespace": "default",
            "resources": {'claims': None,
                 'limits': {'cpu': '2', 'memory': '8000Mi'},
                 'requests': {'cpu': '1', 'memory': '4000Mi'}},
            "pod_info": [
                ["a-a-a-a-12345", "10.244.1.2", "Running"],
                ["a-a-a-a-67890", "10.244.1.3", "Running"]
            ]
        }
        """
        if not self.api:
            self.load_kube_config()

        service= query_data.get('pod', '').strip()
        if not service:
            logging.error(f"查询参数确实，需要提供ip或者pod")
            return None
        try:
            label_selector = f"app={service}"
            pods = self.api.list_pod_for_all_namespaces(label_selector=label_selector, timeout_seconds=30)
            if not pods:
                logging.error(f"未找到与服务标签 '{label_selector}' 匹配的 Pod")
                return None

            # 提取 Pod 信息
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

            # 返回结果
            return {
                "namespace": pods.items[0].metadata.namespace,
                "container": pod.spec.containers[0].name,
                "resources": {
                    "limits": pod.spec.containers[0].resources.limits,
                    'requests': pod.spec.containers[0].resources.requests
                },
                "pod_info": pod_info
            }
        except ApiException as e:
            logging.error(f"调用 Kubernetes API 时发生异常: {e}")
            return None

    def _copy_file_to_local(self, pod_file_path, params):
        """
        将Pod内的文件复制到本地目录
        :param pod_file_path: Pod内的文件绝对路径
        """
        try:
            daily_log_path = os.path.join(self.local_log_path, date_dir, params.get('pod'))
            os.makedirs(daily_log_path, exist_ok=True)

            original_filename = os.path.basename(pod_file_path)  # memory.hprof
            local_path = os.path.join(daily_log_path, original_filename)

            # 构建kubectl cp命令
            cmd = [
                f"/usr/local/bin/kubectl",
                f"--kubeconfig={self.get_cluster_auth_info()}",
                "cp",
                f"{params.get('namespace')}/{params.get('pod')}:{pod_file_path}",
                local_path
            ]
            # 执行复制命令
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            logging.info(f"文件复制成功: {pod_file_path} -> {local_path}")
            return {
                "local_path": local_path,
                "download_url": f"{self.down_log_url}/download/{date_dir}/{params.get('pod')}/{original_filename}"
            }
        except subprocess.CalledProcessError as e:
            error_msg = f"文件复制失败: {e.stderr}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            logging.error(f"文件复制异常: {str(e)}")
            raise

    def get_service_name_by_ip(self, query_data):
        """
        通过IP或者Pod查询Pod完整信息
        :param query_data:
        :return:
        """
        if not self.api:
            self.load_kube_config()

        target_pod = query_data.get('pod', '').strip()
        if not target_pod:
            logging.error(f"查询参数确实，需要提供ip或者pod")
            return None

        try:
            is_ip = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target_pod)
            field_selector = f"status.podIP={target_pod}" if is_ip else f"metadata.name={target_pod}"
            pods = self.api.list_pod_for_all_namespaces(field_selector=field_selector, timeout_seconds=30)
            if not pods:
                logging.error(f"查询不到IP或者Pod: {target_pod}")
                return None
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
            logging.error(f"未找到匹配的Pod: {target_pod}")
            return None
        except client.exceptions.ApiException as api_err:
            logging.error(f"API 调用异常 ｜ 错误信息: {api_err}")
            raise
        except Exception as err:
            logging.error(f"查询IP或者Pod失败: {err}")
            raise

    def check_pods_desc(self, params):
        """
        查询Pod的事件日志
        :return:
        """
        if not self.api:
            self.load_kube_config()
        try:
            pod_obj = self.api.read_namespaced_pod(namespace=params.get('namespace'),
                                                   name=params.get('pod'))
            pod_name =pod_obj.metadata.name
            events = self.api.list_namespaced_event(namespace=params.get('namespace'),
                                                    field_selector=f"involvedObject.name={pod_name}",
                                                    timeout_seconds=30)

            event_messages = [e.message for e in events.items if e.message]
            logging.info(f"Pod事件查询成功 | Name: {pod_name}")
            return "\n".join(event_messages)

        except client.exceptions.ApiException as e:
            logging.error(f"K8S API异常 | 状态码: {e.status} | 详情: {e.reason}")
            raise
        except Exception as err:
            logging.exception(f"Pod事件查询出现未处理异常: {str(err)}")  # 记录完整堆栈
            raise

    def _get_pod_java_pid(self, params):
        """
        获取Pod的Java进程ID
        :return:
        """
        pid_command = ["sh", "-c", "ps -ef | grep java | grep -v grep | awk '{{print $2}}'"]
        try:
            ws_client = stream(self.api.connect_get_namespaced_pod_exec,
                               name=params.get('pod'), namespace=params.get('namespace'), command=pid_command,
                              stderr=True, stdin=False, stdout=True, tty=False,
                              _preload_content=False)
            # 读取WebSocket输出流
            pid = ""
            while ws_client.is_open():
                # 读取标准输出并解码
                output = ws_client.read_stdout()
                if output:
                    pid += output.strip()

            # 验证PID有效性
            if not pid.isdigit():
                logging.error(f"无效的进程ID格式: {pid}")
                return None

            logging.info(f"Pod: {params.get('pod')} 的Java进程ID: {pid}")
            return pid
        except Exception as e:
            logging.error(f"获取Pod: {params.get('pod')} 的Java进程ID失败: {e}")
            return None
        finally:
            # 确保关闭WebSocket连接
            if 'ws_client' in locals():
                ws_client.close()

    def read_last_n_lines(self, file_path, num_lines):
        # 创建一个deque，它最多只保存num_lines行, 避免文件过大
        from collections import deque
        buffer = deque(maxlen=num_lines)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    buffer.append(line)
            return buffer
        except Exception as e:
            logging.error(f"读取文件 {file_path} 时发生错误: {e}")
            return None

    def dump_pod_cpu(self, params):
        """
        获取Pod的CPU 过高、线程死锁、应用卡死
        所有线程的堆栈信息，用于分析 高 CPU 线程、死锁、线程阻塞。
        适用场景：
            1、CPU 过高，查找哪个线程占用 CPU。
            2、线程死锁 分析。
            3、应用卡死、无响应 排查。
        保留：top -H -p <pid>，printf "%x\n" <tid>，jcmd <pid> Thread.print
        :return: 最近 200 行线程 Dump 内容
        """
        if not self.api:
            self.load_kube_config()
        pid = self._get_pod_java_pid(params)
        if not pid:
            logging.error(f"获取不到Pod: {params.get('pod')} 的Java进程ID")
            return None
        output_file = f"{self.pod_log_path}/{params.get('container')}/log/{params.get('pod')}.txt"

        flame_graph_svg = f"{self.pod_log_path}/{params.get('container')}/log/{params.get('pod')}.svg"
        profiler_script_path = f"{self.pod_log_path}/{params.get('container')}/log/async-profiler/profiler.sh"

        # Step 1: 将火焰图目录async-profiler复制到pod的日志路径
        try:
            # 使用 kubectl cp 命令将整个目录复制到 pod
            kubectl_cp_command = (f"kubectl --kubeconfig={self.get_cluster_auth_info()}  cp {self.flame_graph_path} "
                                  f"{params.get('namespace')}/{params.get('pod')}:{self.pod_log_path}/{params.get('container')}/log/")
            result = subprocess.run(kubectl_cp_command, shell=True, check=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            logging.info(f"已成功复制异步分析器 {self.flame_graph_path} 到pod内部.")
        except subprocess.CalledProcessError as e:
            logging.error(f"无法将 async-profiler 目录复制到 pod: {e.stderr.decode()}")
            return None

        # Step 2: 在容器内执行 profiler.sh 脚本来收集 CPU 分析数据
        flame_graph_command = ["sh", "-c", f"{profiler_script_path} -d 60 -f {flame_graph_svg} -e cpu {pid}"]
        try:
            # 在容器内执行profiler.sh脚本
            stream(self.api.connect_get_namespaced_pod_exec,
                   name=params.get('pod'),
                   namespace=params.get('namespace'),
                   command=flame_graph_command,
                   stderr=True, stdin=False, stdout=True, tty=False)
            logging.info(f"Profiler 脚本在 pod 内成功执行.")
            flame_local_path = self._copy_file_to_local(flame_graph_svg, params)
        except Exception as e:
            logging.error(f"无法在 Pod 内执行分析器脚本: {str(e)}")
            return None

        # Step 3: 使用 jcmd 生成线程转储
        jcmd_command_thread = ["sh", "-c", f"{self.jdk_path}/jcmd {pid} Thread.print > {output_file}"]
        try:
            jstat_data = stream(self.api.connect_get_namespaced_pod_exec,
                                name=params.get('pod'), namespace=params.get('namespace'), command=jcmd_command_thread,
                                stderr=True, stdin=False, stdout=True, tty=False,
                                )
            self.cpu_local_path = self._copy_file_to_local(output_file, params)
            with open(self.cpu_local_path.get('local_path'), "r", encoding='utf-8') as f:
                thread_dump_lines = f.readlines()[-200:]
            logging.info(f"成功读取Pod: {params.get('pod')} | 线程Dump文件: {self.cpu_local_path}")

            result = {
                "dump_lines": "\n".join(thread_dump_lines),
                "download_url": self.cpu_local_path.get('download_url'),
                "flame_graph_url": f"{self.down_log_url}/reports/{date_dir}/{params.get('pod')}/{params.get('pod')}.svg"
            }
            return result
        except Exception as e:
            logging.error(f"线程转储文件未生成 | Path: {output_file}， 错误信息: {str(e)}")
            return None


    def dump_pod_heap_memory(self, params):
        """"
        获取Pod的内存泄漏、OOM 分析、大对象排查
        生成 Heap Dump 文件（.hprof），用于 分析内存泄漏、大对象分布。
        适用场景：
            1、内存溢出（OOM）排查。
            2、分析 Java 对象占用情况，找出内存泄漏点。
            3、查看哪些类占用最多的堆内存。
        :return: 最近 200 行 Heap Dump 相关日志
        """
        if not self.api:
            self.load_kube_config()
        pid = self._get_pod_java_pid(params)
        if not pid:
            return "获取不到Pod: {pod_name} 的Java进程ID"
        output_file = f"{self.pod_log_path}/{params.get('container')}/log/{params.get('pod')}.hprof"
        jcmd_command = [f"{self.jdk_path}/jcmd", str(pid), "GC.heap_dump", output_file]
        jcmd_class_hist = [f"{self.jdk_path}/jcmd", str(pid), "GC.class_histogram"]
        try:
            stream(self.api.connect_get_namespaced_pod_exec,
                               name=params.get('pod'), namespace=params.get('namespace'), command=jcmd_command,
                               stderr=True, stdin=False, stdout=True, tty=False,
                               )
            self.heap_path = self._copy_file_to_local(output_file, params)

            logging.info(f"Pod: {params.get('pod')} | Heap Dump 已保存: {output_file}")
            # 执行 class histogram 命令
            hist_client = stream(self.api.connect_get_namespaced_pod_exec,
                                 name=params.get('pod'), namespace=params.get('namespace'), command=jcmd_class_hist,
                                 stderr=True, stdin=False, stdout=True, tty=False)
            # 读取 class histogram 输出
            hist_output = hist_client.strip().split("\n")

            # 取最后 200 行返回
            heap_dump_logs = hist_output[-200:]

            # 新增堆分析脚本调用
            dump_script_path = os.path.join(os.path.dirname(__file__), 'dump.sh')
            if os.path.isfile(dump_script_path):
                try:
                    result = subprocess.run(
                        [dump_script_path, params.get('pod')],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=300  # 5分钟超时
                    )
                    logging.info(f"堆分析输出:\n{result.stdout}")
                except subprocess.CalledProcessError as e:
                    logging.error(f"堆分析失败[code={e.returncode}]:\n{e.stdout}")
                except Exception as e:
                    logging.exception(f"堆分析异常: {str(e)}")
            else:
                logging.warning("堆分析脚本缺失或不可执行")

            result = {
                "dump_lines": "\n".join(heap_dump_logs),
                "download_url": self.heap_path.get('download_url'),
                "heap_analyze_url": f"{self.down_log_url}/reports/{date_dir}/{params.get('pod')}/index.html",
            }
            return result

        except Exception as e:
            logging.error(f"获取Pod: {params.get('pod')} 的Java进程ID失败: {e}")
            return None
@app.route('/k8s', methods=['POST'])
def handle_k8s_request():
    content = request.get_data(as_text=True)
    try:
        data = json.loads(content)
        print(f"Request body: {data}")
        if not data:
            return {"error": "Request body must be JSON"}, 400
        # 校验必要参数
        env =  data.get('env')
        func_name =  data.get('func_name')
        print(env)
        if not all([env, func_name]):
            return {"error": "Request body must contain env and func_name"}, 400
        try:
            k8s_helper = K8sHelper(env=env)
            config = k8s_helper._load_env_config(env)
        except Exception as e:
            return {"error": f"K8sHelper init failed: {str(e)}"}, 500

        params = data

        # 动态获取方法
        if not hasattr(k8s_helper, func_name):
            return {"error": f"Function {func_name} not found"}, 404
        method = getattr(k8s_helper, func_name)

        # 预处理公共参数
        if func_name in ['dump_pod_heap_memory', 'dump_pod_cpu', 'check_pods_desc', 'get_pods_last_logs']:
            params.update(k8s_helper.get_service_name_by_ip(data))
            if not params:
                return {"error": "Pod not found"}, 404
        if func_name in ['scale_deployment']:
            params.update(k8s_helper.get_pod_based_on_service(data))
            if not params:
                return {"error": "Pod not found"}, 404

        print(f"Request params: {params}")
        try:
            result = method(params)
            result.update({"env": config.get('env')})
            result.update({"cluster_name": config.get('cluster_name')})
        except ApiException as e:
            return {"error": f"Kubernetes API error: {str(e)}"}, 500
        except Exception as e:
            return {"error": f"Method execution error: {str(e)}"}, 500
        return {"result": result}, 200

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}, 500

@app.route('/download/<date_dir>/<filename>', methods=['GET'])
def download_file(date_dir, filename):
    """
   下载生成的诊断文件
   :param date_dir: 日期目录 如20230317
   :param filename: 文件名 如memory.hprof
   """
    try:
        # 构造完整路径并验证安全性
        target_dir = os.path.join(os.getenv('local_log_path'), date_dir)

        # 防止路径遍历攻击
        if not os.path.exists(os.path.join(target_dir, filename)):
            return {"error": "非法路径"}, 403

        return send_from_directory(
            directory=target_dir,
            path=filename,
            as_attachment=True  # 作为附件下载
        )
    except FileNotFoundError:
        return {"error": "文件不存在"}, 404

@app.route('/reports/<date_dir>/<project>/<path:filename>')
def reports(date_dir, project, filename):
    target_dir = os.path.join(os.getenv('local_log_path'), date_dir, project)
    if not os.path.exists(os.path.join(target_dir, filename)):
        return "File not found", 404

        # 返回文件
    return send_from_directory(target_dir, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6010)
