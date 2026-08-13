#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：蒸的好 CLI 品牌配置加载器——读 brand.yaml → Brand 对象。
售卖入口：换一个客户 = 复制一份 brand.yaml 改数据，代码框架零改动。
"""
import os

import yaml


class Brand:
    """品牌配置的结构化访问。数据来自 brand.yaml，代码不绑定具体品牌。"""

    def __init__(self, data):
        self.data = data

    # ── 顶层字段 ────────────────────────────────────────────
    @property
    def brand(self):
        return self.data.get("brand", {})

    @property
    def contact(self):
        return self.data.get("contact", {})

    @property
    def story(self):
        return self.data.get("story", {})

    @property
    def quotes(self):
        return self.data.get("quotes", [])

    @property
    def menu(self):
        return self.data.get("menu", {})

    @property
    def tables(self):
        return self.data.get("tables", {})

    @property
    def coupon(self):
        return self.data.get("coupon", {})

    @property
    def fresh_choices(self):
        return self.data.get("fresh_choices", [])

    # ── 派生便捷属性 ────────────────────────────────────────
    @property
    def name(self):
        return self.brand.get("name", "")

    @property
    def sub_name(self):
        return self.brand.get("sub_name", "")

    @property
    def slogan(self):
        return self.brand.get("slogan", "")

    @property
    def established(self):
        return self.brand.get("established", 2015)

    @property
    def tagline(self):
        return self.brand.get("tagline", "")

    @property
    def uptime_years(self):
        return self.brand.get("uptime_years", 0)

    @property
    def rating(self):
        return self.contact.get("dianping", {}).get("rating", "")

    @property
    def phone(self):
        return self.contact.get("phone", "")

    @property
    def address(self):
        return self.contact.get("address", "")

    @property
    def metro(self):
        return self.contact.get("metro", "")

    @property
    def hours(self):
        return self.contact.get("hours", "")

    @property
    def parking(self):
        return self.contact.get("parking", "")

    @property
    def info_items(self):
        """info 命令的有序展示项（中文 label, value 列表）"""
        return self.data.get("info", [])

    @property
    def dianping_url(self):
        shop_id = self.contact.get("dianping", {}).get("shop_id", "")
        return f"https://m.dianping.com/shop/{shop_id}"

    @property
    def all_items(self):
        """菜品编号 → 菜品字典（跨分类展平，供 order/pr 等按编号取菜）"""
        items = {}
        for cat_items in self.menu.values():
            for it in cat_items:
                items[it["id"]] = it
        return items

    @property
    def hot_items(self):
        """所有 hot=True 且定价的招牌菜（供 share/bench 取）"""
        return [i for cat in self.menu.values() for i in cat if i.get("hot")]


def load_brand(path=None):
    """加载品牌配置。查找顺序：显式 path > ZHENG_BRAND 环境变量 > 包目录 brand.yaml。
    售卖时用 ZHENG_BRAND 指向客户自己的 brand.yaml。"""
    if path is None:
        path = os.environ.get("ZHENG_BRAND") or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "brand.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"品牌配置格式错误：{path}")
    return Brand(data)
