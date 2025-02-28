#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  : 模拟实际应用场景中使用 ccconfig

from ccconfig import Config, ConfigItem
import os
import time
import logging
import threading
from datetime import datetime


class Application:
    """模拟一个应用程序"""
    
    def __init__(self):
        # 初始化配置
        self.config = Config(
            auto_reload=True,
            reload_interval=3,
            enable_logging=True,
            log_level=logging.INFO
        )
        
        # 定义配置项
        self._define_config_items()
        
        # 加载配置
        self._load_config()
        
        # 设置配置变更监听
        self._setup_config_watchers()
        
        # 应用状态
        self.running = False
        self.workers = []
    
    def _define_config_items(self):
        """定义配置项"""
        self.config.add_config_item(ConfigItem(
            key="app.name",
            description="应用名称",
            default="MyApplication",
            type=str
        ))
        
        self.config.add_config_item(ConfigItem(
            key="app.environment",
            description="运行环境",
            default="development",
            type=str,
            choices={"development", "testing", "production"}
        ))
        
        self.config.add_config_item(ConfigItem(
            key="server.host",
            description="服务器主机",
            default="127.0.0.1",
            type=str
        ))
        
        self.config.ad