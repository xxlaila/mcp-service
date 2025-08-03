# -*- coding: utf-8 -*-
"""
@File    : swagger_docs.py 
@Time    : 2025/4/10 14:59
@Author  : xxlaila
@Software: dify
"""
from flask import jsonify

def generate_swagger_doc():
    return jsonify({
    	"openapi": "3.0.0",
    	"info": {
    		"title": "K8s Flask Service API",
    		"description": "API for Kubernetes and file operations",
    		"version": "1.0.0",
    		"contact": {
    			"email": "cq_xxlaila@163.com"
    		}
    	},
    	"paths": {
    		"/k8s": {
    			"post": {
    				"tags": ["Kubernetes"],
    				"summary": "处理Kubernetes请求",
    				"description": "用于执行Kubernetes相关操作",
    				"requestBody": {
    					"required": True,
    					"content": {
    						"application/json": {
    							"schema": {
    								"type": "object",
    								"properties": {
    									"env": {
    										"type": "string",
    										"enum": ["dev", "test", "pro"],
    										"description": "目标环境",
    										"example": "pro"
    									},
    									"pod": {
    										"type": "string",
    										"description": "Pod名称/IP/服务",
    										"example": "ugd-eic-main-api"
    									},
    									"func_name": {
    										"type": "string",
    										"description": "要执行的操作函数",
    										"example": "get_pod_based_on_service"
    									}
    								},
    								"required": ["env", "pod", "func_name"]
    							}
    						}
    					}
    				},
    				"responses": {
    					"200": {
    						"description": "操作成功",
    						"content": {
    							"application/json": {
    								"example": {
    									"status": "success",
    									"data": {}
    								}
    							}
    						}
    					},
    					"400": {
    						"description": "无效请求参数",
    						"content": {
    							"application/json": {
    								"example": {
    									"error": "Missing required parameters"
    								}
    							}
    						}
    					},
    					"500": {
    						"description": "服务器内部错误",
    						"content": {
    							"application/json": {
    								"example": {
    									"error": "Internal server error"
    								}
    							}
    						}
    					}
    				}
    			}
    		},
    		"/download/{date_dir}/{project}/{filename}": {
    			"get": {
    				"summary": "Download file",
    				"description": "Endpoint for downloading files",
    				"parameters": [{
    						"name": "date_dir",
    						"in": "path",
    						"required": True,
    						"schema": {
    							"type": "string"
    						}
    					},
    					{
    						"name": "project",
    						"in": "path",
    						"required": True,
    						"schema": {
    							"type": "string"
    						}
    					},
    					{
    						"name": "filename",
    						"in": "path",
    						"required": True,
    						"schema": {
    							"type": "string"
    						}
    					}
    				],
    				"responses": {
    					"200": {
    						"description": "File downloaded successfully"
    					},
    					"404": {
    						"description": "File not found"
    					}
    				}
    			}
    		},
    		"/reports/{date_dir}/{project}/{filename}": {
    			"get": {
    				"summary": "Get reports",
    				"description": "Endpoint for accessing reports",
    				"parameters": [{
    						"name": "date_dir",
    						"in": "path",
    						"required": True,
    						"schema": {
    							"type": "string"
    						}
    					},
    					{
    						"name": "project",
    						"in": "path",
    						"required": True,
    						"schema": {
    							"type": "string"
    						}
    					},
    					{
    						"name": "filename",
    						"in": "path",
    						"required": True,
    						"schema": {
    							"type": "string"
    						}
    					}
    				],
    				"responses": {
    					"200": {
    						"description": "Report retrieved successfully"
    					},
    					"404": {
    						"description": "Report not found"
    					}
    				}
    			}
    		}
    	}
    })