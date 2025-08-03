# -*- coding: utf-8 -*-
"""
@File    : init.py 
@Time    : 2025/4/9 10:14
@Author  : xxlaila
@Software: dify
"""
from flask import Flask
from utils.logger import logger
from utils.config import load_config
from controllers.k8s_controller import handle_k8s_request
from controllers.file_controller import download_file, reports
from flask_swagger_ui import get_swaggerui_blueprint
from docs.swagger_docs import generate_swagger_doc

def create_app(config_name='test'):
    app = Flask(__name__)

    # Load configuration
    if config_name == 'dev':
        from configs.dev import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    elif config_name == 'pro':
        from configs.pro import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from configs.test import TestingConfig
        app.config.from_object(TestingConfig)
    # Load environment variables
    load_config()

    # Swagger UI configuration
    SWAGGER_URL = '/api/docs'
    API_URL = '/api/swagger.json'

    # Call factory function to create our blueprint
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={  # Swagger UI config overrides
            'app_name': "K8s Flask Service API"
        }
    )

    # Register blueprint at URL
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    # Register routes
    app.add_url_rule('/k8s', 'handle_k8s_request', handle_k8s_request, methods=['POST'])
    app.add_url_rule('/download/<date_dir>/<project>/<filename>', 'download_file', download_file, methods=['GET'])
    app.add_url_rule('/reports/<date_dir>/<project>/<path:filename>', 'reports', reports, methods=['GET'])

    @app.route('/api/swagger.json', methods=['GET'])
    def swagger():
        return generate_swagger_doc()

    return app