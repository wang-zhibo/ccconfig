#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  : 展示 ccconfig 的高级功能

from ccconfig import Config, ConfigItem
import os
import json
import time
import logging
import tempfile


def demo_validation():
    """演示配置验证功能"""
    print("\n=== 配置验证功能演示 ===")
    
    cfg = Config()
    
    # 添加带有验证规则的配置项
    cfg.add_config_item(ConfigItem(
        key="app.port",
        description="应用端口",
        default=8080,
        type=int,
        min_value=1000,
        max_value=9999
    ))
    
    cfg.add_config_item(ConfigItem(
        key="app.mode",
        description="应用模式",
        default="development",
        type=str,
        choices={"development", "testing", "production"}
    ))
    
    # 验证有效值
    valid, error = cfg.validate_item("app.port", 8080)
    print(f"验证端口 8080: {'通过' if valid else '失败'} {error or ''}")
    
    valid, error = cfg.validate_item("app.port", 500)
    print(f"验证端口 500: {'通过' if valid else '失败'} {error or ''}")
    
    valid, error = cfg.validate_item("app.mode", "development")
    print(f"验证模式 development: {'通过' if valid else '失败'} {error or ''}")
    
    valid, error = cfg.validate_item("app.mode", "debug")
    print(f"验证模式 debug: {'通过' if valid else '失败'} {error or ''}")


def demo_config_save_load():
    """演示配置保存和加载功能"""
    print("\n=== 配置保存和加载功能演示 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"使用临时目录: {temp_dir}")
    
    # 创建配置
    cfg = Config()
    cfg._set("server.host", "localhost")
    cfg._set("server.port", 8080)
    cfg._set("database.url", "mysql://localhost:3306/mydb")
    cfg._set("database.pool_size", 10)
    cfg._set("logging.level", "INFO")
    
    # 保存为不同格式
    json_path = os.path.join(temp_dir, "config.json")
    yaml_path = os.path.join(temp_dir, "config.yaml")
    ini_path = os.path.join(temp_dir, "config.ini")
    
    cfg.save(json_path)
    print(f"已保存 JSON 配置: {json_path}")
    
    cfg.save(yaml_path, format_type="yaml")
    print(f"已保存 YAML 配置: {yaml_path}")
    
    cfg.save(ini_path, format_type="ini")
    print(f"已保存 INI 配置: {ini_path}")
    
    # 加载配置
    new_cfg = Config()
    new_cfg.load(json_path)
    print(f"\n从 JSON 加载的配置:")
    print(json.dumps(new_cfg.to_dict(), indent=2))


def demo_type_conversion():
    """演示类型转换功能"""
    print("\n=== 类型转换功能演示 ===")
    
    cfg = Config()
    
    # 添加自定义类型转换器
    def convert_list_of_ints(val):
        if isinstance(val, list):
            return [int(x) for x in val]
        if isinstance(val, str):
            return [int(x.strip()) for x in val.split(',')]
        raise ValueError("Cannot convert to list of integers")
    
    cfg.add_type_converter('int_list', convert_list_of_ints)
    
    # 测试内置转换器
    print("内置转换器:")
    print(f"  字符串 'yes' 转布尔值: {cfg._convert_bool('yes')}")
    print(f"  字符串 'no' 转布尔值: {cfg._convert_bool('no')}")
    print(f"  字符串 '1,2,3' 转列表: {cfg._convert_list('1,2,3')}")
    print(f"  字符串 'a=1,b=2' 转字典: {cfg._convert_dict('a=1,b=2')}")
    
    # 测试自定义转换器
    print("\n自定义转换器:")
    print(f"  字符串 '10,20,30' 转整数列表: {cfg._cast_value('10,20,30', convert_list_of_ints)}")


def demo_change_listeners():
    """演示变更监听功能"""
    print("\n=== 变更监听功能演示 ===")
    
    cfg = Config()
    
    # 初始配置
    cfg._set("app.name", "MyApp")
    cfg._set("app.version", "1.0.0")
    cfg._set("app.debug", False)
    
    # 添加监听器
    def on_name_change(old_val, new_val):
        print(f"应用名称从 '{old_val}' 变更为 '{new_val}'")
    
    def on_version_change(old_val, new_val):
        print(f"应用版本从 '{old_val}' 变更为 '{new_val}'")
    
    def on_any_change(old_config, new_config):
        print(f"配置发生变更: {len(old_config)} -> {len(new_config)} 个配置项")
    
    cfg.watch("app.name", on_name_change)
    cfg.watch("app.version", on_version_change)
    cfg.add_change_listener("global_listener", on_any_change)
    
    # 修改配置
    print("修改配置:")
    
    old_data = cfg.to_dict()
    cfg._set("app.name", "NewApp")
    cfg._set("app.version", "2.0.0")
    cfg._set("app.debug", True)
    cfg._notify_change_listeners(old_data, cfg.to_dict())


def main():
    """主函数"""
    print("=== ccconfig 高级功能演示 ===")
    
    demo_validation()
    demo_config_save_load()
    demo_type_conversion()
    demo_change_listeners()
    
    print("\n演示完成!")


if __name__ == "__main__":
    main()