# -*- coding: utf-8 -*-
"""
@File    : file_controller.py 
@Time    : 2025/3/17 14:10
@Author  : xxlaila
@Software: dify
"""
from flask import send_from_directory
import os
from utils.logger import logger

def download_file(date_dir, project, filename):
    try:
        target_dir = os.path.join(os.getenv('local_log_path'), date_dir, project)

        if not os.path.exists(os.path.join(target_dir, filename)):
            return {"error": "File not found"}, 404

        return send_from_directory(
            directory=target_dir,
            path=filename,
            as_attachment=True
        )
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return {"error": "File download failed"}, 500

def reports(date_dir, project, filename):
    try:
        target_dir = os.path.join(os.getenv('local_log_path'), date_dir, project)
        if not os.path.exists(os.path.join(target_dir, filename)):
            return "File not found", 404

        return send_from_directory(target_dir, filename)
    except Exception as e:
        logger.error(f"Report access error: {str(e)}")
        return "Internal server error", 500