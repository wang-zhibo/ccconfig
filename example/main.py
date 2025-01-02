#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  : ccconfig is a lightweight configuration management library for Python.



from ccconfig import Config
import os 
import json


def main():
    # 初始化配置管理器
    cfg = Config()

    # 1. 加载基础配置文件
    cfg.load("config.ini", priority=1)  # 低优先级
    cfg.load("config.yaml", priority=2)  # 高优先级

    # 2. 从环境变量加载配置
    # 设置环境变量示例：
    # export MYAPP_SERVER_PORT=9999
    # export MYAPP_DATABASE_PASSWORD=secret
    cfg.load_env(prefix="MYAPP_")

    # 3. 添加自定义类型转换器
    cfg.add_type_converter('path', os.path.expanduser)

    # 4. 验证配置项
    cfg.validate({
        "server.host": {"cast": str, "default": "localhost"},
        "server.port": {"cast": int, "required": True},
        "server.debug": {"cast": bool, "default": False},
        "database.name": {"cast": str, "required": True},
        "database.password": {"cast": str, "required": True},
        "database.timeout": {"cast": int, "default": 30},
        "user.home_dir": {"cast": "path", "default": "~"}
    })

    # 5. 获取配置值
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

    # 6. 打印配置信息
    print("Server Configuration:")
    for key, value in server_config.items():
        print(f"  {key}: {value} ({type(value).__name__})")

    print("\nDatabase Configuration:")
    for key, value in database_config.items():
        print(f"  {key}: {value} ({type(value).__name__})")

    print("\nUser Configuration:")
    for key, value in user_config.items():
        print(f"  {key}: {value} ({type(value).__name__})")

    # 7. 获取完整配置字典
    full_config = cfg.to_dict()
    print("\nFull Configuration:")
    print(json.dumps(full_config, indent=2))

    # 8. 重新加载配置（适用于配置热更新）
    cfg.reload()

if __name__ == "__main__":
    main()
