#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  :

import os
import json
import time
import logging
import base64
from configparser import ConfigParser
from typing import Any, Dict, Optional, Union, Callable, List, Tuple, Set
from dataclasses import dataclass

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import yaml
except ImportError:
    yaml = None


class Config:
    def __init__(self, auto_reload: bool = False, reload_interval: int = 5, 
                 enable_logging: bool = False, log_level: int = logging.INFO,
                 encryption_key: Optional[str] = None) -> None:
        """Initialize a new Config instance.
        
        Args:
            auto_reload: 是否启用自动重载
            reload_interval: 自动重载间隔时间(秒)
            enable_logging: 是否启用日志记录
            log_level: 日志级别
            encryption_key: 用于加密敏感配置的密钥
        """
        self._config_data: Dict[str, Any] = {}
        self._config_files: List[Tuple[str, int]] = []
        self._config_metadata: Dict[str, ConfigItem] = {}
        self._auto_reload = auto_reload
        self._reload_interval = reload_interval
        self._last_reload_time = 0.0
        self._type_converters: Dict[str, Callable] = {
            'int': int,
            'float': float,
            'bool': self._convert_bool,
            'str': str,
            'list': self._convert_list,
            'dict': self._convert_dict
        }
        self._change_listeners: Dict[str, Callable] = {}
        
        # 初始化日志记录器
        self._logger = logging.getLogger("ccconfig")
        if enable_logging:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(log_level)
        else:
            self._logger.addHandler(logging.NullHandler())
        
        if auto_reload:
            self._start_auto_reload()

    def _start_auto_reload(self) -> None:
        """启动自动重载线程"""
        import threading
        def reload_worker():
            while True:
                try:
                    time.sleep(self._reload_interval)
                    if self._should_reload():
                        self._logger.info("检测到配置文件变更，正在重新加载")
                        self.reload()
                except Exception as e:
                    self._logger.error(f"自动重载过程中发生错误: {e}")
                    
        thread = threading.Thread(target=reload_worker, daemon=True, name="ConfigReloader")
        thread.start()
        self._logger.info(f"已启动配置自动重载线程，间隔: {self._reload_interval}秒")

    def _should_reload(self) -> bool:
        """判断是否需要重载"""
        try:
            for filepath, _ in self._config_files:
                if not os.path.exists(filepath):
                    self._logger.warning(f"配置文件已不存在: {filepath}")
                    continue
                    
                if os.path.getmtime(filepath) > self._last_reload_time:
                    self._logger.debug(f"配置文件已更改: {filepath}")
                    return True
        except Exception as e:
            self._logger.error(f"检查配置文件变更时出错: {e}")
        return False

    def add_change_listener(self, name: str, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]) -> None:
        """Add a change listener that will be called when configuration changes.
        
        Args:
            name: Unique identifier for the listener
            callback: Function that takes (old_config, new_config) as arguments
        """
        self._change_listeners[name] = callback

    def remove_change_listener(self, name: str) -> None:
        """Remove a previously registered change listener.
        
        Args:
            name: Unique identifier of the listener to remove
        """
        self._change_listeners.pop(name, None)

    def _notify_change_listeners(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """Notify all registered listeners about configuration changes.
        
        Args:
            old_config: Configuration before changes
            new_config: Configuration after changes
        """
        for listener in self._change_listeners.values():
            try:
                listener(old_config, new_config)
            except Exception as e:
                # Prevent one failing listener from breaking others
                print(f"Error in config change listener: {e}")

    def add_config_item(self, item: ConfigItem) -> None:
        """添加配置项元数据"""
        self._config_metadata[item.key] = item
        if item.default is not None:
            self._set(item.key, item.default)

    def get_config_metadata(self, key: str) -> Optional[ConfigItem]:
        """获取配置项元数据"""
        return self._config_metadata.get(key)

    def get_description(self, key: str) -> Optional[str]:
        """获取配置项描述"""
        item = self.get_config_metadata(key)
        return item.description if item else None

    def load(self, filepath: str, priority: int = 0) -> None:
        """Load configuration from file.
        
        Args:
            filepath: Path to configuration file. Supported formats: .ini/.cfg, .json, .yaml/.yml
            priority: Priority level for this configuration (higher values take precedence)
            
        Raises:
            FileNotFoundError: If the specified file does not exist
            ValueError: If the file format is not supported
            ImportError: If YAML file is provided but PyYAML is not installed
        """
        if not os.path.isfile(filepath):
            self._logger.error(f"配置文件未找到: {filepath}")
            raise FileNotFoundError(f"Config file not found: {filepath}")
    
        self._logger.info(f"加载配置文件: {filepath} (优先级: {priority})")
        self._config_files.append((filepath, priority))
        self._config_files.sort(key=lambda x: x[1])
    
        new_data = {}
        for f, _ in self._config_files:
            loaded_data = self._load_file(f)
            new_data = self._merge_dict(new_data, loaded_data)
        
        # Notify listeners of changes
        old_data = self._config_data
        self._config_data = new_data
        self._notify_change_listeners(old_data, new_data)
        self._last_reload_time = time.time()

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

    def watch(self, key: str, callback: Callable[[Any, Any], None]) -> None:
        """监听配置项变化"""
        def listener(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
            old_val = self._get_nested(old_config, key)
            new_val = self._get_nested(new_config, key)
            if old_val != new_val:
                callback(old_val, new_val)
        self.add_change_listener(f"watch_{key}", listener)

    def _get_nested(self, config: Dict[str, Any], key: str) -> Any:
        """获取嵌套配置值"""
        keys = key.split('.')
        cur = config
        for k in keys:
            if k not in cur:
                return None
            cur = cur[k]
        return cur

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
        def save(self, filepath: str, format_type: str = None) -> None:
            """将当前配置保存到文件
            
            Args:
                filepath: 保存的文件路径
                format_type: 文件格式，支持 'json', 'yaml', 'ini'，如果为 None 则根据文件扩展名自动判断
            
            Raises:
                ValueError: 如果文件格式不支持
                ImportError: 如果需要 PyYAML 但未安装
            """
            if format_type is None:
                ext = os.path.splitext(filepath)[1].lower()
                if ext in ('.json'):
                    format_type = 'json'
                elif ext in ('.yaml', '.yml'):
                    format_type = 'yaml'
                elif ext in ('.ini', '.cfg'):
                    format_type = 'ini'
                else:
                    raise ValueError(f"无法从文件扩展名确定格式: {ext}")
            
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            if format_type == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self._config_data, f, ensure_ascii=False, indent=2)
            elif format_type == 'yaml':
                if yaml is None:
                    raise ImportError("PyYAML 未安装，请安装它以支持 YAML 格式")
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config_data, f, allow_unicode=True)
            elif format_type == 'ini':
                parser = ConfigParser()
                for section, values in self._config_data.items():
                    if isinstance(values, dict):
                        parser.add_section(section)
                        for key, value in values.items():
                            if isinstance(value, (str, int, float, bool)):
                                parser.set(section, key, str(value))
                with open(filepath, 'w', encoding='utf-8') as f:
                    parser.write(f)
            else:
                raise ValueError(f"不支持的文件格式: {format_type}")

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

    def validate_item(self, key: str, value: Any) -> Tuple[bool, Optional[str]]:
        """验证单个配置项是否符合元数据定义的规则
        
        Args:
            key: 配置项键名
            value: 配置项值
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        metadata = self.get_config_metadata(key)
        if not metadata:
            return True, None
        
        # 类型检查
        if metadata.type is not None:
            try:
                if isinstance(metadata.type, str):
                    converter = self._type_converters.get(metadata.type)
                    if converter is None:
                        return False, f"未知的类型转换器: {metadata.type}"
                    self._cast_value(value, converter)
                else:
                    self._cast_value(value, metadata.type)
            except (ValueError, TypeError):
                return False, f"值 '{value}' 无法转换为类型 {metadata.type}"
        
        # 选项检查
        if metadata.choices is not None and value not in metadata.choices:
            return False, f"值 '{value}' 不在允许的选项范围内: {metadata.choices}"
        
        # 数值范围检查
        if isinstance(value, (int, float)):
            if metadata.min_value is not None and value < metadata.min_value:
                return False, f"值 '{value}' 小于最小值 {metadata.min_value}"
            if metadata.max_value is not None and value > metadata.max_value:
                return False, f"值 '{value}' 大于最大值 {metadata.max_value}"
        
        return True, None

    def validate_all(self) -> Dict[str, str]:
        """验证所有已定义元数据的配置项
        
        Returns:
            Dict[str, str]: 验证失败的配置项及错误信息
        """
        errors = {}
        for key, metadata in self._config_metadata.items():
            value = self.get(key)
            if value is None:
                if metadata.required:
                    errors[key] = "缺少必需的配置项"
                continue
            
            valid, error = self.validate_item(key, value)
            if not valid:
                errors[key] = error
        
        return errors

    def add_type_converter(self, name: str, converter: Callable) -> None:
        """添加自定义类型转换器"""
        self._type_converters[name] = converter

    def watch(self, key: str, callback: Callable[[Any, Any], None]) -> None:
        """监听配置项变化"""
        def listener(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
            old_val = self._get_nested(old_config, key)
            new_val = self._get_nested(new_config, key)
            if old_val != new_val:
                callback(old_val, new_val)
        self.add_change_listener(f"watch_{key}", listener)

    def _get_nested(self, config: Dict[str, Any], key: str) -> Any:
        """获取嵌套配置值"""
        keys = key.split('.')
        cur = config
        for k in keys:
            if k not in cur:
                return None
            cur = cur[k]
        return cur

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
        def save(self, filepath: str, format_type: str = None) -> None:
            """将当前配置保存到文件
            
            Args:
                filepath: 保存的文件路径
                format_type: 文件格式，支持 'json', 'yaml', 'ini'，如果为 None 则根据文件扩展名自动判断
            
            Raises:
                ValueError: 如果文件格式不支持
                ImportError: 如果需要 PyYAML 但未安装
            """
            if format_type is None:
                ext = os.path.splitext(filepath)[1].lower()
                if ext in ('.json'):
                    format_type = 'json'
                elif ext in ('.yaml', '.yml'):
                    format_type = 'yaml'
                elif ext in ('.ini', '.cfg'):
                    format_type = 'ini'
                else:
                    raise ValueError(f"无法从文件扩展名确定格式: {ext}")
            
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            if format_type == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self._config_data, f, ensure_ascii=False, indent=2)
            elif format_type == 'yaml':
                if yaml is None:
                    raise ImportError("PyYAML 未安装，请安装它以支持 YAML 格式")
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config_data, f, allow_unicode=True)
            elif format_type == 'ini':
                parser = ConfigParser()
                for section, values in self._config_data.items():
                    if isinstance(values, dict):
                        parser.add_section(section)
                        for key, value in values.items():
                            if isinstance(value, (str, int, float, bool)):
                                parser.set(section, key, str(value))
                with open(filepath, 'w', encoding='utf-8') as f:
                    parser.write(f)
            else:
                raise ValueError(f"不支持的文件格式: {format_type}")

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
