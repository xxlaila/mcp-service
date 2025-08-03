# -*- coding: utf-8 -*-
"""
@File    : diagnostics.py 
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
import subprocess
import os
from datetime import datetime
from kubernetes.stream import stream

class Diagnostics:
    def __init__(self, api_client, core_api, config):
        self.api = core_api
        self.config = config
        self.date_dir = datetime.now().strftime("%Y%m%d")

    def _get_pod_java_pid(self, params):
        pid_command = ["sh", "-c", "ps -ef | grep java | grep -v grep | awk '{{print $2}}'"]
        try:
            ws_client = stream(
                self.api.connect_get_namespaced_pod_exec,
                name=params.get('pod'),
                namespace=params.get('namespace'),
                command=pid_command,
                stderr=True, stdin=False, stdout=True, tty=False,
                _preload_content=False
            )

            pid = ""
            while ws_client.is_open():
                output = ws_client.read_stdout()
                if output:
                    pid += output.strip()

            if not pid.isdigit():
                return None
            return pid
        except Exception:
            return None
        finally:
            if 'ws_client' in locals():
                ws_client.close()

    def _copy_file_to_local(self, pod_file_path, params):
        try:
            daily_log_path = os.path.join(self.config.local_log_path, self.date_dir, params.get('pod'))
            os.makedirs(daily_log_path, exist_ok=True)
            original_filename = os.path.basename(pod_file_path)
            local_path = os.path.join(daily_log_path, original_filename)

            cmd = [
                f"/usr/local/bin/kubectl",
                f"--kubeconfig={self.config.get_cluster_auth_info()}",
                "cp",
                f"{params.get('namespace')}/{params.get('pod')}:{pod_file_path}",
                local_path
            ]

            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            return {
                "local_path": local_path,
                "download_url": f"{self.config.down_log_url}/download/{self.date_dir}/{params.get('pod')}/{original_filename}"
            }
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"文件复制失败: {e.stderr}")