#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：蒸的好 CLI 真 AI 问答模块——DeepSeek API，未配置 api_key 时由 zheng.py 降级为离线关键词问答。
配置：zheng config set api_key <你的 DeepSeek Key>
"""
import json
import urllib.error
import urllib.request

import storage
from zheng import BRAND

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


def build_system_prompt():
    """带品牌上下文 + 实时菜单的 system prompt"""
    lines = []
    for cat, lst in BRAND.menu.items():
        for it in lst:
            tag = " 🔥" if it.get("hot") else ""
            p = "时价" if it["price"] is None else f"¥{it['price']}/{it['unit']}"
            lines.append(f"{it['id']} {it['name']} {p}{tag} — {it['desc']}")
    menu_block = "\n".join(lines)
    return (
        f"你是「{BRAND.name}」的AI管家——{BRAND.sub_name}"
        f"（{BRAND.tagline}，蒸汽锁鲜，大众点评{BRAND.rating}分，0食品安全事故）。\n"
        "回答风格：\n"
        "1. 简洁精确，能用数字不用形容词；\n"
        "2. 推荐菜时引用菜单编号和价格，可加一句程序员梗（O(1)、纯函数、uptime、debug），但别堆砌；\n"
        f"3. 门店信息：地址 {BRAND.address}，电话 {BRAND.phone}，营业 {BRAND.hours}；\n"
        "4. 不知道的如实说不知道，不编造。\n"
        "菜单：\n" + menu_block
    )


def ask_ai(question):
    """调用 DeepSeek 对话补全。返回 (回答文本 or None, 模型名/错误说明)。"""
    cfg = storage.load_config()
    api_key = cfg.get("api_key", "")
    if not api_key:
        return None, "离线模式"

    model = cfg.get("model", DEFAULT_MODEL)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"], model
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, "连接超时"
    except (KeyError, json.JSONDecodeError):
        return None, "响应异常"
