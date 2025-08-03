# -*- coding: utf-8 -*-
"""
@File    : app.py 
@Time    : 2025/4/15 19:14
@Author  : xxlaila
@Software: dify
"""
import logging
from flask import Flask
from controllers import monitor_controller
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# 配置日志
logging.basicConfig(
    level=app.config['LOG_LEVEL'],
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 注册蓝图
app.register_blueprint(monitor_controller.monitor_bp, url_prefix='/api')

if __name__ == '__main__':
    logger.info(f"Starting MCP Server on port {app.config['PORT']}")
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'])