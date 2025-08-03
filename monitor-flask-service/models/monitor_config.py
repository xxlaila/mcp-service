# -*- coding: utf-8 -*-
"""
@File    : monitor_config.py
@Time    : 2025/4/15 19:13
@Author  : xxlaila
@Software: dify
"""
from dataclasses import dataclass

@dataclass
class MonitorConfig:
    link: str
    height: int
    width: int = 1902