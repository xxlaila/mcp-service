# -*- coding: utf-8 -*-
"""
@File    : monitor_controller.py 
@Time    : 2025/4/15 19:13
@Author  : xxlaila
@Software: dify
"""
import json
from flask import Blueprint, request, jsonify, send_from_directory
from helpers.monitor_helper import MonitorHelper, FuncName
import logging
import os
from utils.response import success, fail

monitor_bp = Blueprint('monitor', __name__)
logger = logging.getLogger(__name__)

def _initialize_grafana_helper():
    """初始化 GrafanaHelper，返回实例或错误响应"""
    try:
        return MonitorHelper(), None
    except ValueError as e:
        logger.error(f"Failed to initialize MonitorHelper: {str(e)}")
        return None, fail(f"Failed to initialize MonitorHelper: {str(e)}", 500)

def _parse_request_data(content):
    """解析请求数据，返回解析后的数据或错误响应"""
    try:
        data = json.loads(content)
        if not data or "func_name" not in data:
            logger.error("No JSON data provided")
            return None, fail("No JSON data provided", 400)

        try:
            FuncName(data.get("func_name"))
        except ValueError as e:
            logger.error(f"Invalid function name: {str(e)}")
            return None, fail(f"Invalid function name: {str(e)}", 400)

        return data, None
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return None, fail(f"Invalid JSON format: {str(e)}", 400)
    except Exception as e:
        logger.error(f"Unexpected error parsing request: {str(e)}")
        return None, fail(f"Invalid request data: {str(e)}", 400)

def _get_method(func_name, grafana_helper):
    """根据 func_name 获取对应的处理方法，返回方法或错误响应"""
    try:
        func_name_enum = FuncName(func_name)
    except ValueError as e:
        logger.error(f"Invalid function name: {str(e)}")
        return None, fail(f"Invalid function name: {str(e)}", 400)

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

    method = method_mapping.get(func_name_enum)
    if not method:
        logger.error(f"Unsupported function: {func_name}")
        return None, fail(f"Unsupported function: {func_name}", 400)

    return method, None

@monitor_bp.route('/tools', methods=['GET'])
def get_tools():
    """获取当前服务支持的所有工具名称"""
    """获取当前服务支持的所有工具及其参数"""
    tools_info = {}
    parameter_mapping = {
        FuncName.K8S_SERVICE_NAME.value: ["cluster", "namespace", "container", "pod"],
        FuncName.K8S_RESOURCE.value: ["cluster"],
        FuncName.ELB.value: ["ip"],
        FuncName.CLB.value: ["ip"],
        FuncName.ELASTICSEARCH.value: ["name"],
        FuncName.ZOOKEEPER.value: ["name"],
        FuncName.LINUX.value: ["ip"],
        FuncName.MONGODB.value: ["name"],
        FuncName.MYSQL.value: ["ip"],
        FuncName.REDIS.value: ["name"],
    }

    for func in FuncName:
        tools_info[func.value] = {"parameters": parameter_mapping.get(func.value, [])}

    return success({"tools": tools_info})
    # tools = [func.value for func in FuncName]
    # return success({"tools": tools})

@monitor_bp.route('/tools/<string:tool_name>/parameters', methods=['GET'])
def get_tool_parameters(tool_name):
    """获取指定工具所需的参数列表"""
    try:
        func_name = FuncName(tool_name)
    except ValueError:
        return fail(f"Invalid tool name: {tool_name}", 400)

    # 在这里定义每个工具需要的参数
    parameter_mapping = {
        FuncName.K8S_SERVICE_NAME: ["env", "cluster", "namespace", "container"],
        FuncName.K8S_RESOURCE: ["env", "cluster"],
        FuncName.ELB: ["ip"],
        FuncName.CLB: ["ip"],
        FuncName.ELASTICSEARCH: ["name"],
        FuncName.ZOOKEEPER: ["env", "name"],
        FuncName.LINUX: ["ip"],
        FuncName.MONGODB: ["name"],
        FuncName.MYSQL: ["ip"],
        FuncName.REDIS: ["name"],
    }

    parameters = parameter_mapping.get(func_name)
    if parameters is None:
        return fail(f"Parameters for tool '{tool_name}' not defined.", 500)

    return success({"tool_name": tool_name, "parameters": parameters})

@monitor_bp.route('/monitor', methods=['POST'])
def handle_monitor_request():
    """处理监控请求，下载 Grafana 图片"""
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
    func_name = data.get("func_name")
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
        return fail(str(e), 400)
    except Exception as e:
        logger.exception("Unexpected error processing request")
        return fail(f"Internal server error: {str(e)}", 500)