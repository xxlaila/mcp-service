# -*- coding: utf-8 -*-
"""
@File    : main.py 
@Time    : 2025/3/24 16:25
@Author  : xxlaila
@Software: dify
"""
import json
import re, sys, os
import datetime
import time,requests
from requests_toolbelt import MultipartEncoder
from flask import Flask, request, send_from_directory, jsonify
from dotenv import load_dotenv
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any

app = Flask(__name__)

logger = logging.getLogger(__name__)

class FuncName(Enum):
    K8S_SERVICE_NAME = "k8s_service_name"
    K8S_RESOURCE = "k8s_resource"
    ELB = "elb"
    CLB = "clb"
    ELASTICSEARCH = "elasticsearch"
    ZOOKEEPER = "zookeeper"
    LINUX = "linux"
    MONGODB = "mongodb"
    MYSQL = "mysql"
    REDIS = "redis"

@dataclass
class GrafanaConfig:
    link: str
    height: int
    width: int = 1902

class GrafanaHelper:
    DEFAULT_WIDTH = 1902
    DEFAULT_OTHER_PARAMS = ""

    def __init__(self):
        load_dotenv()
        self.grafana_server = os.getenv('grafan_url')
        if not self.grafana_server:
            raise ValueError("Grafana server URL is not configured")
        self.api_token = os.getenv('api_token')
        if not self.api_token:
            raise ValueError("API token is not configured")
        self.other_paras = os.getenv('other_paras', self.DEFAULT_OTHER_PARAMS)

    def _load_config(self, func_name: FuncName) -> GrafanaConfig:
        """解析.env中的字典结构配置"""
        try:
            # 读取原始环境变量
            raw_env = os.getenv(func_name.value, '{}')
            # 将字符串转换为Python字典
            config_data = json.loads(raw_env)
            if not config_data.get('link'):
                raise ValueError(f"Missing 'link' in {func_name.value} config")
            height = config_data.get('height')
            if not height or not isinstance(height, int):
                raise ValueError(f"Invalid or missing 'height' in {func_name.value} config")

            return GrafanaConfig(
                link=config_data['link'],
                height=height,
                width=config_data.get('width', self.DEFAULT_WIDTH)
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {func_name.value} config: {e}")
        except Exception as e:
            raise ValueError(f"Error loading {func_name.value} config: {e}")

    def _build_url(self, panel_path: str, config: GrafanaConfig) -> str:
        """构建完整的Grafana URL"""
        return (
            f'/render/{panel_path}'
            f'&width={config.width}'
            f'&height={config.height}'
            f'&{self.other_paras}'
        )

    def _handle_cloud_specific_params(self, params: Dict[str, Any], ip_fields: Tuple[str, str]) -> str:
        """处理云服务商特定的参数"""
        cloud = params.get("cloud", "").lower()
        ip = params.get("ip", "")

        if cloud == "tencent":
            return f"var-{ip_fields[0]}={ip}&var-{ip_fields[1]}="
        return f"var-{ip_fields[0]}=&var-{ip_fields[1]}={ip}"

    def k8s_service_name(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.K8S_SERVICE_NAME)
        required = ["env", "cluster", "namespace", "container"]
        if any(p not in params for p in required):
            raise ValueError(f"Missing required parameters: {required}")

        panel = config.link.format(params.get('env'), params.get('cluster'), params.get('namespace'),
                                   params.get('container'))
        return self._build_url(panel, config)

    def k8s_resource(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.K8S_RESOURCE)
        required = ["env", "cluster"]
        if any(p not in params for p in required):
            raise ValueError(f"Missing required parameters: {required}")

        panel = config.link.format(params.get('env'), params.get('cluster'))
        return self._build_url(panel, config)

    def elb(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.ELB)
        if "ip" not in params:
            raise ValueError("Missing 'ip' parameter")

        # 保留云服务商特定的参数
        # vars = self._handle_cloud_specific_params(params, ("eip", "publicIpAddress"))
        panel = config.link.format(f"var-eip={params.get('ip')}&var-publicIpAddress={params.get('ip')}")
        return self._build_url(panel, config)

    def clb(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.CLB)
        if "ip" not in params:
            raise ValueError("Missing 'ip' parameter")

        # 保留云服务商特定的参数
        # vars = self._handle_cloud_specific_params(params, ("vip", "vip_address"))
        panel = config.link.format(f"var-vip={params.get('ip')}&var-vip_address={params.get('ip')}")
        return self._build_url(panel, config)

    def elasticsearch(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.ELASTICSEARCH)
        panel = config.link.format(params.get('name'))
        return self._build_url(panel, config)

    def zookeeper(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.ZOOKEEPER)
        required = ["env", "name"]
        if any(p not in params for p in required):
            raise ValueError(f"Missing required parameters: {required}")

        panel = config.link.format(params.get('env'), params.get('name'))
        return self._build_url(panel, config)

    def linux(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.LINUX)
        if "ip" not in params:
            raise ValueError("Missing 'ip' parameter")

        panel = config.link.format(params["ip"])
        return self._build_url(panel, config)

    def mongodb(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.MONGODB)
        if "name" not in params:
            raise ValueError("Missing 'name' parameter")

        # 保留云服务商特定的参数
        # vars = self._handle_cloud_specific_params(params, ("instance_name", "name"))
        panel = config.link.format(f"var-instance_name={params.get('name')}&var-name={params.get('name')}")
        return self._build_url(panel, config)

    def mysql(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.MYSQL)
        if "ip" not in params:
            raise ValueError("Missing 'ip' parameter")

        panel = config.link.format(params.get('ip'))
        return self._build_url(panel, config)

    def redis(self, params: Dict[str, Any]) -> str:
        config = self._load_config(FuncName.REDIS)
        if "name" not in params:
            raise ValueError("Missing 'ip' parameter")

        # 保留云服务商特定的参数
        # vars = self._handle_cloud_specific_params(params, ("instance_name", "name"))
        panel = config.link.format(f"var-instance_name={params.get('name')}&var-name={params.get('name')}")
        return self._build_url(panel, config)

    def get_time(self) -> Tuple[str, str]:
        """获取当前时间和1小时前的时间戳"""
        now = datetime.datetime.now()
        end_time = int(now.timestamp() * 1000)
        start_time = int((now - datetime.timedelta(hours=1)).timestamp() * 1000)
        return str(start_time), str(end_time)

    def download_pic(self, url: str) -> str:
        """下载Grafana图片并返回本地文件名"""
        full_url = f"{self.grafana_server}{url}"
        logger.info(f"Downloading image from: {full_url}")

        headers = {
            "Accept": "image/png,image/jpeg",
            "Authorization": f"Bearer {self.api_token}"
        }

        try:
            response = requests.get(full_url, headers=headers, timeout=30)
            time.sleep(3)
            response.raise_for_status()

            if not response.content:
                raise ValueError("Empty response from Grafana")

            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            img_name = f"img_{timestamp}.png"

            with open(img_name, "wb") as f:
                f.write(response.content)

            return img_name

        except requests.RequestException as e:
            logger.error(f"Failed to download image: {str(e)}")
            raise ValueError(f"Failed to download image from Grafana: {str(e)}")
        except IOError as e:
            logger.error(f"Failed to save image: {str(e)}")
            raise ValueError(f"Failed to save image: {str(e)}")

# 路由处理函数
@app.route('/monitor', methods=['POST'])
def handle_monitor_request():
    content = request.get_data(as_text=True)
    logger.info(f"Received monitor request")

    # 初始化 GrafanaHelper
    grafana_helper, error_response = _initialize_grafana_helper()
    if error_response:
        return error_response

    # 解析请求数据
    data, error_response = _parse_request_data(content)
    if error_response:
        return error_response

    # 获取对应的处理方法
    func_name = FuncName(data.get("func_name"))
    method, error_response = _get_method(func_name, grafana_helper)
    if error_response:
        return error_response

    try:
        # 生成 Grafana URL
        grafana_url = method(data)

        img_path = grafana_helper.download_pic(grafana_url)
        return send_from_directory(
            os.getcwd(),
            img_path,
            as_attachment=True,
            mimetype='image/png'
        )
    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Unexpected error processing request")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

def _initialize_grafana_helper():
    """初始化 GrafanaHelper，返回实例或错误响应"""
    try:
        return GrafanaHelper(), None
    except ValueError as e:
        logger.error(f"Failed to initialize GrafanaHelper: {str(e)}")
        return None, jsonify({"error": f"Failed to initialize GrafanaHelper: {str(e)}"}), 500

def _parse_request_data(content):
    """解析请求数据，返回解析后的数据或错误响应"""
    try:
        data = json.loads(content)
        if not data or "func_name" not in data:
            logger.error("No JSON data provided")
            return None, jsonify({"error": "No JSON data provided"}), 400

        func_name = FuncName(data.get("func_name"))
        return data, None
    except ValueError as e:
        logger.error(f"Invalid function name: {str(e)}")
        return None, jsonify({"error": f"Invalid function name: {str(e)}"}), 400
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return None, jsonify({"error": f"Invalid JSON format: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Unexpected error parsing request: {str(e)}")
        return None, jsonify({"error": f"Invalid request data: {str(e)}"}), 400

def _get_method(func_name, grafana_helper):
    """根据 func_name 获取对应的处理方法，返回方法或错误响应"""
    try:
        func_name = FuncName(func_name)  # 确保 func_name 是有效的枚举值
    except ValueError as e:
        logger.error(f"Invalid function name: {str(e)}")
        return None, jsonify({"error": f"Invalid function name: {str(e)}"}), 400

    method_mapping = {
        FuncName.K8S_SERVICE_NAME: grafana_helper.k8s_service_name,
        FuncName.K8S_RESOURCE: grafana_helper.k8s_resource,
        FuncName.ELB: grafana_helper.elb,
        FuncName.CLB: grafana_helper.clb,
        FuncName.ELASTICSEARCH: grafana_helper.elasticsearch,
        FuncName.ZOOKEEPER: grafana_helper.zookeeper,
        FuncName.LINUX: grafana_helper.linux,
        FuncName.MONGODB: grafana_helper.mongodb,
        FuncName.MYSQL: grafana_helper.mysql,
        FuncName.REDIS: grafana_helper.redis,
    }

    method = method_mapping.get(func_name)
    if not method:
        logger.error(f"Unsupported function: {func_name.value}")
        return None, jsonify({"error": f"Unsupported function: {func_name.value}"}), 400

    return method, None

if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 启动应用
    app.run(host='0.0.0.0', port=6011, debug=False)