# -*- coding: utf-8 -*-
"""
@File    : decorators.py 
@Time    : 2025/4/10 10:35
@Author  : xxlaila
@Software: dify
"""
import functools
import traceback
from utils.logger import logger

def k8s_operation(name=None):
    """统一处理K8s操作的错误和日志"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = name or func.__name__
            try:
                logger.info(f"开始执行操作: {op_name}")
                result = func(*args, **kwargs)
                logger.info(f"操作 {op_name} 执行成功")
                return result
            except Exception as e:
                logger.error(f"操作 {op_name} 失败: {str(e)}", exc_info=True)
                return {
                    "success": False,
                    "error": f"{op_name} failed",
                    "details": {
                        "operation": op_name,
                        "error": str(e),
                        "stack_trace": traceback.format_exc()
                    }
                }
        return wrapper
    return decorator