#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  :


import os
import json
from configparser import ConfigParser
try:
    import yaml
except ImportError:
    yaml = None


class Config:
    def __init__(self):
        # 用于存储最终合并后的配置数据
        self._config_data = {}
        # 记录已加载的文件及其优先级 (priority)
        self._config_files = []

    def load(self, filepath, priority=0):
        """
        加载指定配置文件。
        priority 值越大，优先级越高，会覆盖之前相同 key。
        支持 .ini/.cfg, .json, .yaml/.yml 文件。
        """
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Config file not found: {filepath}")

        self._config_files.append((filepath, priority))
        # 按优先级排序（先低后高，后加载的覆盖先加载的）
        self._config_files.sort(key=lambda x: x[1])

        # 重新按照排序结果，依次合并到 _config_data
        new_data = {}
        for f, _pri in self._config_files:
            loaded_data = self._load_file(f)
            new_data = self._merge_dict(new_data, loaded_data)
        self._config_data = new_data

    def load_env(self, prefix=""):
        """
        从环境变量中加载配置。仅加载以 prefix 开头的环境变量。
        加载后会覆盖同名 key（优先级最高）。
        """
        env_data = {}
        for k, v in os.environ.items():
            if k.startswith(prefix):
                # 移除前缀后存储
                short_key = k[len(prefix):]
                # 也可自行设计如何处理层级，这里简单存储为顶层 key
                env_data[short_key] = v

        # 由于是“最后”加载，优先级最高，覆盖之前的
        self._config_data = self._merge_dict(self._config_data, env_data)

    def get(self, key, default=None, cast=None):
        """
        通过点号分隔访问配置。例如 "database.host" 对应 self._config_data["database"]["host"]。
        如果找不到则返回 default。
        如果指定了 cast，会尝试进行类型转换（如 int/bool/float 等）。
        """
        keys = key.split('.')
        cur = self._config_data
        for k in keys:
            if k not in cur:
                return default
            cur = cur[k]

        if cast is not None:
            try:
                cur = self._cast_value(cur, cast)
            except (ValueError, TypeError):
                # 如果转换失败，返回 default 或者根据需要抛出异常
                return default

        return cur

    def __getitem__(self, key):
        """
        使得 cfg["database.host"] 等价于 cfg.get("database.host")。
        """
        return self.get(key)

    def validate(self, schema):
        """
        进行基础的字段校验：
        schema 示例:
        {
            "server.port": {"cast": int, "required": True},
            "server.debug": {"cast": bool, "default": False}
        }
        - required: 是否必填
        - default: 如果未提供则使用该默认值
        - cast: 指定转换类型，如 int, bool, float 等
        """
        for key, rules in schema.items():
            required = rules.get("required", False)
            default_val = rules.get("default", None)
            cast_type = rules.get("cast", None)

            current_val = self.get(key, default=None, cast=None)
            if current_val is None:
                if required:
                    raise ValueError(f"Missing required config key: {key}")
                # 如果不必填但有默认值，则设置为默认值
                if default_val is not None:
                    self._set(key, default_val)
            else:
                # 如果指定了类型(cast)，则进行转换并更新
                if cast_type is not None:
                    try:
                        converted_val = self._cast_value(current_val, cast_type)
                        self._set(key, converted_val)
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f"Key '{key}' cannot be converted to {cast_type.__name__}: {e}"
                        )

    # -----------------------
    # 内部辅助方法
    # -----------------------
    def _load_file(self, filepath):
        """
        根据扩展名 (.ini/.cfg, .json, .yaml/.yml) 加载文件并返回 dict。
        """
        ext = os.path.splitext(filepath)[1].lower()
        if ext in (".ini", ".cfg"):
            parser = ConfigParser()
            parser.read(filepath, encoding="utf-8")
            return self._configparser_to_dict(parser)
        elif ext == ".json":
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif ext in (".yaml", ".yml"):
            if yaml is None:
                raise ImportError("PyYAML is not installed. Please install it to parse YAML.")
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _configparser_to_dict(self, parser):
        """
        将 ConfigParser 对象转换成嵌套的 dict。
        """
        data = {}
        for section in parser.sections():
            data[section] = {}
            for key, val in parser.items(section):
                data[section][key] = val
        return data

    def _merge_dict(self, base, override):
        """
        递归地将 override 字典合并到 base 字典中（override 覆盖 base）。
        """
        for k, v in override.items():
            if (
                k in base
                and isinstance(base[k], dict)
                and isinstance(v, dict)
            ):
                base[k] = self._merge_dict(base[k], v)
            else:
                base[k] = v
        return base

    def _set(self, key, value):
        """
        根据点号分隔，向 self._config_data 中写入值。
        例如 key="server.port" 会写入 self._config_data["server"]["port"]。
        """
        keys = key.split('.')
        cur = self._config_data
        for i, k in enumerate(keys):
            if i == len(keys) - 1:
                cur[k] = value
            else:
                if k not in cur:
                    cur[k] = {}
                cur = cur[k]

    def _cast_value(self, val, cast_type):
        """
        执行类型转换，如 int, bool, float 等。
        对 bool 做了简单的字符串判断，可根据需求自行扩展。
        """
        if cast_type is bool:
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                lower_val = val.lower()
                if lower_val in ["true", "yes", "1"]:
                    return True
                elif lower_val in ["false", "no", "0"]:
                    return False
                else:
                    raise ValueError(f"Cannot interpret '{val}' as bool.")
            return bool(val)

        # 其它类型 (int, float, 等)
        return cast_type(val)

