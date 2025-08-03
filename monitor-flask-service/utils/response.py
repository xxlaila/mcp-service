# -*- coding: utf-8 -*-
"""
@File    : response.py 
@Time    : 2025/4/15 19:13
@Author  : xxlaila
@Software: dify
"""
from flask import jsonify

def success(data=None, message="Success", status_code=200):
    """返回成功的 JSON 响应"""
    response = {"code": 0, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code

def fail(message="Error", status_code=400, data=None):
    """返回失败的 JSON 响应"""
    response = {"code": 1, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code