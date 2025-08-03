# -*- coding: utf-8 -*-
"""
@File    : k8s_controller.py
@Time    : 2025/3/17 16:52
@Author  : xxlaila
@Software: dify
"""
from flask import request
from models.k8s_model import K8sModel
from utils.logger import logger
import json

def handle_k8s_request():
    content = request.get_data(as_text=True)
    try:
        data = json.loads(content)
        logger.info(f"Request body: {data}")
        if not data:
            return {"error": "Request body must be JSON"}, 400

        env = data.get('env')
        func_name = data.get('func_name')
        if not all([env, func_name]):
            return {"error": "Request body must contain env and func_name"}, 400

        try:
            k8s_model = K8sModel(env=env)
            config = k8s_model._load_env_config(env)
            result = k8s_model.execute_method(func_name, data.copy())
            print(f"result: {result}")
            return {
                "result": {
                    **result,
                    "env": config.get('env'),
                    "cluster_name": config.get('cluster_name')
                }
            }, 200

        except ValueError as e:
            return {"error": str(e)}, 404
        except AttributeError:
            return {"error": f"Function {func_name} not found"}, 404
        except Exception as e:
            logger.error(f"Method execution error: {str(e)}")
            return {"error": f"Method execution error: {str(e)}"}, 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}, 500