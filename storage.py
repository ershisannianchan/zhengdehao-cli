#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：蒸的好 CLI 统一持久化层——数据目录、JSON 读写、配置读写。
规则：所有运行时数据（订单/桌位/暗号/核销日志）统一落到 ~/.zheng/data/，
     可用环境变量 ZHENG_HOME 覆盖根目录（兼顾 D 盘偏好），不污染包目录。
"""
import json
import os


def _home():
    """根目录：默认 ~/.zheng，可用 ZHENG_HOME 覆盖"""
    return os.environ.get("ZHENG_HOME", os.path.join(os.path.expanduser("~"), ".zheng"))


def config_dir():
    return _home()


def data_dir():
    return os.path.join(_home(), "data")


# ── JSON 读写 ──────────────────────────────────────────────

def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass  # 读取失败返回默认值，由调用方决定提示
    return default


def save_json(data, path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


# ── 配置（~/.zheng/config.json：api_key / model / nickname）──

def config_file():
    return os.path.join(config_dir(), "config.json")


def load_config():
    return load_json(config_file())


def save_config(cfg):
    return save_json(cfg, config_file())


# ── 运行时数据路径 ──────────────────────────────────────────

def orders_path():
    return os.path.join(data_dir(), "orders.json")


def tables_path():
    return os.path.join(data_dir(), "tables.json")


def codes_path():
    return os.path.join(data_dir(), "codes.json")


def ledger_path():
    return os.path.join(data_dir(), "ledger.jsonl")


def image_map_path():
    return os.path.join(data_dir(), "image_map.json")
