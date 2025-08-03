# -*- coding: utf-8 -*-
"""
@File    : swagger_docs.py
@Time    : 2025/4/10 14:59
@Author  : xxlaila
@Software: dify
"""
from flask import jsonify

def generate_swagger_doc(tools):
    # 动态生成 Paths 和 Components
    paths = {}
    schemas = {}

    for tool in tools:
        # 为每个工具生成对应的 API 路径
        paths[f"/call_tool/{tool['name']}"] = {
            "post": {
                "tags": ["Tools"],
                "summary": tool["description"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "parameters": {
                                        "type": "object",
                                        "properties": tool["parameters"],
                                        "required": [k for k, v in tool["parameters"].items() if v.get("required")]
                                    }
                                },
                                "required": ["parameters"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": tool["returns"]
                                }
                            }
                        }
                    },
                    "400": {"description": "Invalid input"},
                    "404": {"description": "Tool not found"}
                }
            }
        }

        # 为每个工具生成对应的 Schema（可选）
        schemas[f"Tool_{tool['name']}"] = {
            "type": "object",
            "properties": tool["parameters"]
        }

    # 完整的 Swagger 文档
    swagger_doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "Elasticsearch Flask Service API",
            "description": "API for Elasticsearch and file operations",
            "version": "1.0.0",
            "contact": {
                "email": "cq_xxlaila@163.com"
            }
        },
        "paths": paths,
        "components": {
            "schemas": schemas
        }
    }
    return jsonify(swagger_doc)