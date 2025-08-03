# -*- coding: utf-8 -*-
"""
@File    : utils.py 
@Time    : 2025/4/10 10:37
@Author  : xxlaila
@Software: dify
"""
import subprocess, os
import traceback
import functools
from contextlib import contextmanager
from kubernetes.stream import stream
from utils.logger import logger
from ..utils.decorators import k8s_operation
from ..utils.context_managers import k8s_command_execution
from ..utils.path_utils import PodPathUtils

class PodDiagnostics:
    def __init__(self, diagnostics, config):
        self.diagnostics = diagnostics
        self.config = config
        self.path_utils = PodPathUtils()

    @k8s_operation("获取Java进程PID")
    def _get_java_pid(self, params):
        pid = self.diagnostics._get_pod_java_pid(params)
        if not pid:
            raise ValueError(f"未找到Pod {params.get('pod')}中的Java进程")
        return pid

    @k8s_operation("复制文件到Pod")
    def _copy_to_pod(self, source, pod_name, namespace, dest_path):
        cmd = (f"kubectl --kubeconfig={self.config.get_cluster_auth_info()} "
               f"cp {source} {namespace}/{pod_name}:{dest_path}")

        with k8s_command_execution(f"复制文件到Pod {pod_name}"):
            result = subprocess.run(
                cmd, shell=True, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
        return result

    @k8s_operation("生成CPU火焰图")
    def _generate_flame_graph(self, pod_name, namespace, script_path, pid, output_path):
        cmd = ["sh", "-c", f"{script_path} -d 60 -f {output_path} -e cpu {pid}"]
        with k8s_command_execution("生成火焰图"):
            stream(
                self.diagnostics.api.connect_get_namespaced_pod_exec,
                name=pod_name,
                namespace=namespace,
                command=cmd,
                stderr=True, stdin=False, stdout=True, tty=False
            )
        return self.diagnostics._copy_file_to_local(output_path, {
            "pod": pod_name,
            "namespace": namespace
        })

    @k8s_operation("dump_pod_cpu")
    def dump_pod_cpu(self, params):
        # 获取参数
        pod_name = params.get('pod')
        namespace = params.get('namespace')
        container = params.get('container')

        # 获取PID
        pid = self._get_java_pid(params)

        # 准备路径
        base_path = self.path_utils.get_pod_log_path(self.config, pod_name, container)
        script_path = f"{base_path}/async-profiler/profiler.sh"
        output_files = {
            "thread_dump": f"{base_path}/{pod_name}.txt",
            "flame_graph": f"{base_path}/{pod_name}.svg"
        }

        # 复制分析工具
        self._copy_to_pod(self.config.flame_graph_path, pod_name, namespace, base_path)

        # 生成火焰图
        flame_path = self._generate_flame_graph(pod_name, namespace, script_path, pid, output_files["flame_graph"])

        # 获取线程转储
        thread_dump = self._execute_jcmd(pod_name, namespace, pid, f"Thread.print > {output_files['thread_dump']}")
        thread_dump_local = self.diagnostics._copy_file_to_local(output_files["thread_dump"], params)

        # 读取结果
        with open(thread_dump_local.get('local_path'), "r", encoding='utf-8') as f:
            thread_dump_lines = f.readlines()[-200:]

        return {
            "success": True,
            "dump_lines": "\n".join(thread_dump_lines),
            "download_url": thread_dump_local.get('download_url'),
            "flame_graph_url": self.path_utils.get_report_url(
                self.config, self.diagnostics.date_dir, pod_name, f"{pod_name}.svg")
        }

    @k8s_operation("dump_pod_heap_memory")
    def dump_pod_heap_memory(self, params):
        # 获取参数
        pod_name = params.get('pod')
        namespace = params.get('namespace')
        container = params.get('container')

        # 获取PID
        pid = self._get_java_pid(params)

        # 准备路径
        heap_path = self.path_utils.get_pod_log_path(self.config, pod_name, container, f"{pod_name}.hprof")

        # 生成堆转储
        self._execute_jcmd(pod_name, namespace, pid, f"GC.heap_dump {heap_path}")
        heap_local = self.diagnostics._copy_file_to_local(heap_path, params)

        # 获取类直方图
        hist_output = self._execute_jcmd(pod_name, namespace, pid, "GC.class_histogram")
        hist_lines = hist_output.strip().split("\n")[-200:]

        # 堆分析脚本调用
        dump_script_path = os.path.join(os.path.dirname(__file__), 'dump.sh')
        if os.path.isfile(dump_script_path):
            try:
                result = subprocess.run(
                    [dump_script_path, pod_name],  # 使用当前参数中的pod_name
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=300  # 保持5分钟超时
                )
                logger.info(f"堆分析完成: {result.stdout}")
            except subprocess.CalledProcessError as e:
                logger.error(f"堆分析失败[code={e.returncode}]: {e.stdout}")
            except Exception as e:
                logger.exception(f"堆分析异常: {str(e)}")
        else:
            logger.warning("未找到堆分析脚本: dump.sh")

        return {
            "success": True,
            "dump_lines": "\n".join(hist_lines),
            "download_url": heap_local.get('download_url'),
            "heap_analyze_url": self.path_utils.get_report_url(
                self.config, self.diagnostics.date_dir, pod_name, "index.html")
        }

    def _execute_jcmd(self, pod_name, namespace, pid, command):
        """执行jcmd命令的公共方法"""
        full_cmd = [f"{self.config.jdk_path}/jcmd", str(pid)] + command.split()
        with k8s_command_execution(f"执行jcmd命令: {' '.join(full_cmd)}"):
            return stream(
                self.diagnostics.api.connect_get_namespaced_pod_exec,
                name=pod_name,
                namespace=namespace,
                command=full_cmd,
                stderr=True, stdin=False, stdout=True, tty=False
            )