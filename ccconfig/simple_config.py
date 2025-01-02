#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  :



import os
import json
from configparser import ConfigParser
from typing import Any, Dict, Optional, Union, Callable
try:
    import yaml
except ImportError:
    yaml = None


class Config:
    def __init__(self):
        self._config_data = {}
        self._config_files = []
        self._type_converters = {
            'int': int,
            'float': float,
            'bool': self._convert_bool,
            'str': str,
            'list': self._convert_list,
            'dict': self._convert_dict
        }

    def load(self, filepath: str, priority: int = 0) -> None:
        """加载配置文件，支持 .ini/.cfg, .json, .yaml/.yml 格式"""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Config file not found: {filepath}")

        self._config_files.append((filepath, priority))
        self._config_files.sort(key=lambda x: x[1])

        new_data = {}
        for f, _ in self._config_files:
            loaded_data = self._load_file(f)
            new_data = self._merge_dict(new_data, loaded_data)
        self._config_data = new_data

    def load_env(self, prefix: str = "") -> None:
        """从环境变量加载配置"""
        env_data = {}
        for k, v in os.environ.items():
            if k.startswith(prefix):
                short_key = k[len(prefix):]
                env_data[short_key] = v
        self._config_data = self._merge_dict(self._config_data, env_data)

    def get(self, key: str, default: Any = None, cast: Optional[Union[type, str, Callable]] = None) -> Any:
        """获取配置值，支持类型转换"""
        keys = key.split('.')
        cur = self._config_data
        for k in keys:
            if k not in cur:
                return default
            cur = cur[k]

        if cast is not None:
            try:
                if isinstance(cast, str):
                    cast = self._type_converters.get(cast)
                    if cast is None:
                        raise ValueError(f"Unknown type converter: {cast}")
                cur = self._cast_value(cur, cast)
            except (ValueError, TypeError):
                return default

        return cur

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def validate(self, schema: Dict[str, Dict[str, Any]]) -> None:
        """验证配置项"""
        for key, rules in schema.items():
            required = rules.get("required", False)
            default_val = rules.get("default", None)
            cast_type = rules.get("cast", None)

            current_val = self.get(key, default=None, cast=None)
            if current_val is None:
                if required:
                    raise ValueError(f"Missing required config key: {key}")
                if default_val is not None:
                    self._set(key, default_val)
            else:
                if cast_type is not None:
                    try:
                        converted_val = self._cast_value(current_val, cast_type)
                        self._set(key, converted_val)
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f"Key '{key}' cannot be converted to {cast_type.__name__}: {e}"
                        )

    def add_type_converter(self, name: str, converter: Callable) -> None:
        """添加自定义类型转换器"""
        self._type_converters[name] = converter

    def to_dict(self) -> Dict[str, Any]:
        """返回当前配置的完整字典"""
        return self._config_data

    def reload(self) -> None:
        """重新加载所有配置文件"""
        files = [f for f, _ in self._config_files]
        self._config_files = []
        for filepath in files:
            self.load(filepath)

    def _load_file(self, filepath: str) -> Dict[str, Any]:
        """根据文件扩展名加载配置文件"""
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

    def _configparser_to_dict(self, parser: ConfigParser) -> Dict[str, Any]:
        """将 ConfigParser 转换为字典"""
        data = {}
        for section in parser.sections():
            data[section] = {}
            for key, val in parser.items(section):
                data[section][key] = val
        return data

    def _merge_dict(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并字典"""
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

    def _set(self, key: str, value: Any) -> None:
        """设置配置值"""
        keys = key.split('.')
        cur = self._config_data
        for i, k in enumerate(keys):
            if i == len(keys) - 1:
                cur[k] = value
            else:
                if k not in cur:
                    cur[k] = {}
                cur = cur[k]

    def _cast_value(self, val: Any, cast_type: Union[type, Callable]) -> Any:
        """执行类型转换"""
        if cast_type is bool:
            return self._convert_bool(val)
        return cast_type(val)

    def _convert_bool(self, val: Any) -> bool:
        """转换布尔值"""
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            lower_val = val.lower()
            if lower_val in ["true", "yes", "1"]:
                return True
            elif lower_val in ["false", "no", "0"]:
                return False
        return bool(val)

    def _convert_list(self, val: Union[str, list]) -> list:
        """转换列表"""
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return [item.strip() for item in val.split(',')]
        return list(val)

    def _convert_dict(self, val: Union[str, dict]) -> dict:
        """转换字典"""
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return {k.strip(): v.strip() for k, v in (item.split('=') for item in val.split(','))}
        return dict(val)

