# -*- coding: utf-8 -*-
"""
@File    : app.py
@Time    : 2025/4/2 16:30
@Author  : xxlaila
@Software: dify
"""
from flask import Flask
from routes.api import api_bp
from flask_swagger_ui import get_swaggerui_blueprint

SWAGGER_URL = '/api/docs'
API_URL = '/api/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Elasticsearch API文档"}
)
app = Flask(__name__)
app.register_blueprint(api_bp, url_prefix='')
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6012)