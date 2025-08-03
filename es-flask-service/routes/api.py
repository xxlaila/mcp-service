# -*- coding: utf-8 -*-
"""
@File    : api.py 
@Time    : 2025/4/2 16:51
@Author  : xxlaila
@Software: dify
"""
import json,re
from typing import Dict, Any
from utils.logger import logger
from flask import Blueprint, request, jsonify, make_response
from controllers.query_controller import execute_query
from docs.swagger_docs import generate_swagger_doc
from urllib.parse import urlparse, parse_qs
from models.es_client import ESHttpClient
from .tool_suggestions import generate_tool_suggestions

api_bp = Blueprint('api', __name__)

TOOLS = [
    {
        "name": "query",
        "description": "执行Elasticsearch标准DSL查询，json 必须是一个字符串",
        "parameters": {
            "cluster_name": {
                "type": "string",
                "description": "Elasticsearch集群名称（必须由Agent根据上下文显式传入），",
                "required": True,
                "example": "es-app"
            },
            "dsl": {
                "type": "object",
                "description": "查询DSL结构（JSON格式）",
                "required": True,
                "example": {"query": {"match_all": {}}}
            }
        },
        "returns": {
            "type": "object",
            "description": "查询结果，包含命中数据及聚合统计等"
        },
        "parameters_order": ["cluster_name", "dsl"]
    },
    {
        "name": "command",
        "description": "执行Elasticsearch原生命令（如 _cat、_cluster、_nodes 等），必须增加参数， json 必须是一个字符串",
        "parameters": {
            "cluster_name": {
                "type": "string",
                "description": "Elasticsearch集群名称（必须由Agent根据上下文显式传入）,",
                "required": True,
                "example": "es-app"
            },
            "action": {
                "type": "string",
                "description": "命令路径及参数（如：_cat/nodes?v&h=name,heap.percent）",
                "required": True,
                "example": "_cat/nodes?v&h=name,heap.percent"
            }
        },
        "returns": {
            "type": "object",
            "description": "命令执行结果（结构化JSON或文本）",
            "properties": {
                "output": {
                    "type": "string",
                    "description": "命令返回的内容（部分字段过滤后）"
                },
                "format": {
                    "type": "string",
                    "description": "返回内容格式，如 text、json"
                }
            }
        },
        "parameters_order": ["cluster_name", "action"]
    }
]

ALLOWED_PATH_PREFIXES = [
    '_cat',
    '_cluster',
    '_nodes',
    '_tasks',
    'indices',
    '_mapping',
    '_settings',
    '_search',
    '_explain'
]

TYPE_MAP = {
    "string": str,
    "object": dict,
    "number": (int, float),
    "boolean": bool
}

def validate_parameters(parameters: Dict[str, Any], tool_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证工具参数是否符合预期的类型和必填要求。
    """
    errors = []
    for param_name, param_schema in tool_schema.items():
        if param_schema.get('required') and param_name not in parameters:
            errors.append(f"Missing required parameter '{param_name}'")
            continue

        expected_type = TYPE_MAP.get(param_schema['type'])
        actual_value = parameters.get(param_name)
        if expected_type and not isinstance(actual_value, expected_type):
            errors.append(f"Parameter '{param_name}' must be of type {param_schema['type']}")

    if errors:
        raise ValueError("; ".join(errors))
    return parameters

@api_bp.route('/api/swagger.json', methods=['GET'])
def serve_swagger_json():
    from docs.swagger_docs import generate_swagger_doc
    return generate_swagger_doc(TOOLS)

@api_bp.route('/tool_suggestions', methods=['POST'])
def tool_suggestions():
    """
    根据用户输入生成推荐的工具调用列表。
    ---
    tags:
      - 工具推荐
    responses:
      200:
        description: 返回工具建议
    """
    try:
        suggestions = generate_tool_suggestions()
        print(suggestions)
        return jsonify({"suggestions": suggestions}), 200
    except Exception as e:
        logger.exception("Error generating tool suggestions")
        return jsonify({
            "error": str(e)
        }), 500


def create_json_response(data, status_code=200):
    """
    创建标准JSON响应（保持Unicode转义）
    """
    # response = make_response(jsonify(data))
    response = make_response(json.dumps(data, ensure_ascii=False))
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.status_code = status_code
    return response

@api_bp.route('/list_tools', methods=['GET'])
def list_tools():
    """
    列出所有可用工具
    ---
    tags:
      - 工具
    responses:
      200:
        description: 返回工具列表
    """
    response_data = {"tools": [tool.copy() for tool in TOOLS]}
    return create_json_response(response_data)

@api_bp.route('/call_tool', methods=['POST'])
def call_tools():
    """
    调用指定工具
    ---
    tags:
      - 工具
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: 工具名称（query/command）
              required: true
            parameters:
              type: object
              description: 工具参数
              required: true
    responses:
      200:
        description: 调用成功
      400:
        description: 参数错误
      404:
        description: 工具不存在
      500:
        description: 系统错误
    """
    try:
        content = request.get_data(as_text=True)
        logger.info(f"call_tools: {content}")
        data = json.loads(content)

        tool_name = data.get('name')
        if not tool_name:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": "Missing required parameter 'name'"}
            }), 400

        tool = next((t for t in TOOLS if t['name'] == tool_name), None)
        if not tool:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
            }), 404

        parameters = data.get('parameters', {})
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters.replace("'", '"'))
            except json.JSONDecodeError:
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Invalid parameters format (must be valid JSON)"}
                }), 400

        # 参数校验
        try:
            validate_parameters(parameters, tool['parameters'])
        except ValueError as e:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": str(e)}
            }), 400

        if tool_name == 'query':
            cluster_name = parameters['cluster_name']
            dsl = parameters['dsl']
            if not isinstance(dsl, dict) or 'query' not in dsl:
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Invalid DSL format"}
                }), 400
            result = execute_query(cluster_name, dsl)
            return jsonify({"result": {"output": result, "format": "json"}}), 200

        elif tool_name == 'command':
            cluster_name = parameters['cluster_name']
            action = parameters['action']

            path, params = parse_action_path_and_params(action)
            if not is_path_allowed(path):
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": f"Disallowed path: {path}"}
                }), 403

            es = ESHttpClient.get_client(cluster_name)
            if not es.ping():
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Cannot connect to Elasticsearch cluster"}
                }), 500

            try:
                response = es.transport.perform_request(
                    method='GET',
                    url=f'/{path.lstrip("/")}',
                    params=params
                )
                logger.info(f"response: {response}")
                return jsonify({"result": {"output": response, "format": "json"}}), 200
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": str(e)}
                }), 500

    except json.JSONDecodeError:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Invalid JSON format"}
        }), 400

    except Exception as e:
        logger.exception("Unexpected error occurred")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": str(e)}
        }), 500


def is_path_allowed(path: str) -> bool:
    cleaned = path.lstrip('/')
    parts = cleaned.split('/')

    if len(parts) == 2 and parts[1] in ('_mapping', '_settings'):
        return True

    # 允许格式: index/_explain 或 index/_search/_explain
    if len(parts) >= 2 and parts[-1] == '_explain':
        return True

    # 安全检查：禁止直接访问索引的_search
    if re.search(r'^[^/]+/_search$', cleaned):
        return False

    return any(cleaned.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)

def parse_action_path_and_params(action: str):
    parsed = urlparse(action)
    path = parsed.path
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()} if parsed.query else {}
    return path, params