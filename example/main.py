#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  : ccconfig is a lightweight configuration management library for Python.

from ccconfig import Config, ConfigItem
import os 
import json
import time


def main():
    # 初始化配置管理器，启用自动重载
    cfg = Config(auto_reload=True, reload_interval=5)

    # 1. 定义配置项元数据
    cfg.add_config_item(ConfigItem(
        key="server.host",
        description="服务器主机地址",
        default="localhost",
        type=str
    ))
    cfg.add_config_item(ConfigItem(
        key="server.port",
        description="服务器端口号",
        required=True,
        type=int,
        min_value=1024,
        max_value=65535
    ))
    cfg.add_config_item(ConfigItem(
        key="server.debug",
        description="是否启用调试模式",
        default=False,
        type=bool
    ))
    cfg.add_config_item(ConfigItem(
        key="database.name",
        description="数据库名称",
        required=True,
        type=str
    ))
    cfg.add_config_item(ConfigItem(
        key="database.password",
        description="数据库密码",
        required=True,
        type=str
    ))
    cfg.add_config_item(ConfigItem(
        key="database.timeout",
        description="数据库连接超时时间",
        default=30,
        type=int,
        min_value=1
    ))
    cfg.add_config_item(ConfigItem(
        key="user.home_dir",
        description="用户主目录",
        default="~",
        type="path"
    ))

    # 2. 加载配置文件
    cfg.load("config.ini", priority=1)  # 低优先级
    cfg.load("config.yaml", priority=2)  # 高优先级

    # 3. 从环境变量加载配置
    cfg.load_env(prefix="MYAPP_")

    # 4. 添加自定义类型转换器
    cfg.add_type_converter('path', os.path.expanduser)

    # 5. 验证配置项
    cfg.validate({
        "server.host": {"cast": str},
        "server.port": {"cast": int},
        "server.debug": {"cast": bool},
        "database.name": {"cast": str},
        "database.password": {"cast": str},
        "database.timeout": {"cast": int},
        "user.home_dir": {"cast": "path"}
    })

    # 6. 添加配置项监听
    def on_port_change(old_val, new_val):
        print(f"\n[Config Change] server.port changed from {old_val} to {new_val}")
    
    cfg.watch("server.port", on_port_change)

    # 7. 获取配置值
    server_config = {
        "host": cfg.get("server.host"),
        "port": cfg.get("server.port"),
        "debug": cfg.get("server.debug")
    }

    database_config = {
        "name": cfg["database.name"],  # 使用 [] 语法糖
        "password": cfg["database.password"],
        "timeout": cfg["database.timeout"]
    }

    user_config = {
        "home_dir": cfg.get("user.home_dir", cast="path")
    }

    # 8. 打印配置信息
    print("Server Configuration:")
    for key, value in server_config.items():
        print(f"  {key}: {value} ({type(value).__name__})")

    print("\nDatabase Configuration:")
    for key, value in database_config.items():
        print(f"  {key}: {value} ({type(value).__name__})")

    print("\nUser Configuration:")
    for key, value in user_config.items():
        print(f"  {key}: {value} ({type(value).__name__})")

    # 9. 获取完整配置字典
    full_config = cfg.to_dict()
    print("\nFull Configuration:")
    print(json.dumps(full_config, indent=2))

    # 10. 保持程序运行以观察自动重载
    print("\nWaiting for config changes... (Ctrl+C to exit)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
