#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用途：brand.yaml 加载与菜单结构测试（数据外置后数据完整性守护）。"""
import brand


def test_load_brand_basic():
    b = brand.load_brand()
    assert b.name == "蒸的好海鲜馆"
    assert b.phone == "0755-26922888"


def test_menu_structure():
    b = brand.load_brand()
    assert len(b.menu) == 9                       # 9 大分类
    total = sum(len(v) for v in b.menu.values())
    assert total == 115                           # 115 道菜


def test_all_items_flat():
    b = brand.load_brand()
    assert len(b.all_items) == 115
    assert b.all_items["L01"]["name"] == "麻辣牛肉"
    assert b.all_items["L01"]["price"] == 48


def test_market_price_items():
    b = brand.load_brand()
    assert b.all_items["H05"]["price"] is None    # 东星斑 = 时价


def test_hot_items_flag():
    b = brand.load_brand()
    assert all(i.get("hot") for i in b.hot_items)
    assert len(b.hot_items) > 0
