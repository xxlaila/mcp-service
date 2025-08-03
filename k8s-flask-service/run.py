# -*- coding: utf-8 -*-
"""
@File    : run.py
@Time    : 2025/4/8 11:52
@Author  : xxlaila
@Software: dify
"""
from init import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6010)