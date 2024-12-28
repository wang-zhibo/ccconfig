#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  : ccconfig is a lightweight configuration management library for Python.


import cprintf

from ccconfig import Config

def main():
    cfg = Config()

    # 1. 加载 INI (优先级=1)
    cfg.load("config.ini", priority=1)

    # 2. 加载 YAML (优先级=2) - 会覆盖同名 key
    cfg.load("config.yaml", priority=2)

    # 3. 从环境变量加载 (prefix="MYAPP_")
    #    例如：MYAPP_SERVER_PORT=9999 会覆盖 server.port
    cfg.load_env(prefix="MYAPP_")

    # 验证部分字段 (如果没有就报错或填默认值)
    cfg.validate({
        "server.port": {"cast": int, "required": True},
        "server.debug": {"cast": bool, "default": False},
        "database.password": {"cast": str, "required": True},
        "database.timeout": {"cast": int, "default": 30}
    })

    # 读取配置
    host = cfg.get("server.host", default="localhost")
    port = cfg.get("server.port", default=80, cast=int)
    debug = cfg.get("server.debug", default=False, cast=bool)
    db_name = cfg["database.name"]  # 等价于 cfg.get("database.name")
    db_password = cfg["database.password"]
    db_timeout = cfg.get("database.timeout", cast=int)

    # 打印查看
    cprintf.info("Server Config:")
    cprintf.info(f"  host = {host}")
    cprintf.info(f"  port = {port}")
    cprintf.info(f"  debug = {debug}")

    cprintf.info("Database Config:")
    cprintf.info(f"  name = {db_name}")
    cprintf.info(f"  password = {db_password}")
    cprintf.info(f"  timeout = {db_timeout}")

if __name__ == "__main__":
    main()

