#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：蒸的好 CLI 分享卡片生成（终端 ASCII 卡 + 二维码 + share.html 截图版），传播导向。
注册：由 zheng.py 文件末尾 cli.add_command(...) 挂载。
"""
import os
import random

import click
import qrcode

from zheng import BRAND, c, banner, divider, get_or_create_member_code


def qr_ascii_lines(url):
    """二维码 → 字符矩阵行（终端与 HTML 共用）"""
    qr = qrcode.QRCode(border=1, box_size=1)
    qr.add_data(url)
    qr.make(fit=True)
    return ["".join("██" if v else "  " for v in row) for row in qr.get_matrix()]


def card_text():
    """生成卡片文本行。返回 (行列表, 会员码)"""
    quote = random.choice(BRAND.quotes) if BRAND.quotes else {"zh": ""}
    fresh = random.choice(BRAND.fresh_choices) if BRAND.fresh_choices else ""
    secret = get_or_create_member_code()
    hot = [i for cat in BRAND.menu.values() for i in cat if i.get("hot") and i["price"] is not None][:2]
    hot_line = "🍽 必点：" + " · ".join(f"{i['name']} ¥{i['price']}" for i in hot) if hot else "🍽 招牌菜详见菜单"
    discount = BRAND.coupon.get("discount", "全场8折")
    exclude = BRAND.coupon.get("exclude", "")
    lines = [
        f"🦞 {BRAND.name} · {BRAND.tagline} · 蒸汽锁鲜",
        f"Established {BRAND.established} · {BRAND.uptime_years}y uptime · 大众点评 {BRAND.rating}",
        "──────────────",
        f"「{quote.get('zh', '')}」",
        "──────────────",
        f"🔥 今日直采：{fresh}",
        hot_line,
        "──────────────",
        f"🎟️ 专属会员码：{secret}",
        f"📍 到店报码 → {discount}（{exclude}）· 长期有效不限次数",
        "──────────────",
        "📱 扫码看套餐·评价·下单：",
        BRAND.dianping_url,
    ]
    return lines, secret


def build_html(card_lines, qr_lines, secret):
    qr_pre = "\n".join(qr_lines)
    card_pre = "\n".join(card_lines)
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{name} · 分享卡片</title>
<style>
  body {{ background:#0d1117; color:#c9d1d9; font-family:'Cascadia Code','SF Mono',Consolas,'Noto Sans Mono CJK SC',monospace; display:flex; flex-direction:column; align-items:center; padding:40px; }}
  .card {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:28px 34px; box-shadow:0 8px 30px rgba(0,0,0,.5); max-width:520px; }}
  h1 {{ color:#58a6ff; font-size:20px; margin:0 0 4px; }}
  .sub {{ color:#8b949e; font-size:13px; margin-bottom:12px; }}
  pre {{ white-space:pre; line-height:1.1; }}
  .qr {{ color:#3fb950; }}
  .secret {{ color:#d29922; font-size:15px; margin-top:10px; }}
  .hint {{ color:#8b949e; font-size:12px; margin-top:22px; }}
</style>
</head>
<body>
<div class="card">
  <h1>🦞 {name} · {tagline}</h1>
  <div class="sub">Established {established} · {uptime}y uptime · 大众点评 {rating}</div>
  <pre>{card_pre}</pre>
  <div class="qr"><pre>{qr_pre}</pre></div>
  <div class="secret">🎟️ 会员码：{secret}（报码 {discount}，{exclude} · 长期有效）</div>
  <div class="hint">浏览器截图保存，或 Ctrl+P 导出为图片/PDF 分享</div>
</div>
</body>
</html>""".format(
        name=BRAND.name, tagline=BRAND.tagline, established=BRAND.established,
        uptime=BRAND.uptime_years, rating=BRAND.rating, secret=secret,
        discount=BRAND.coupon.get("discount", "全场8折"),
        exclude=BRAND.coupon.get("exclude", ""),
        card_pre=card_pre, qr_pre=qr_pre)


@click.command()
def share():
    """📤 分享卡片（终端显示 + 生成 share.html 可截图）"""
    banner()
    print(c("  📤 分享卡片", "bold"))
    divider()

    card_lines, secret = card_text()
    if not secret:
        print(c("  ❌ 未配置签名密钥，无法生成会员码", "red"))
        print(c("  💡 请设置 ZHENG_SECRET 环境变量，或写入 ~/.zheng/secret", "yellow"))
        print()
        return
    qr_lines = qr_ascii_lines(BRAND.dianping_url)

    print()
    for ln in card_lines:
        print(c(ln, "white"))
    print()
    print(c("  📱 大众点评（截图可扫）：", "yellow"))
    for ln in qr_lines:
        print(c(ln, "green"))
    print()

    html = build_html(card_lines, qr_lines, secret)
    out = os.path.join(os.getcwd(), "zheng_share.html")
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(c(f"  📄 已生成截图版：{out}", "green"))
        print(c(f"  → 浏览器打开 → 截图 / Ctrl+P 导出 → 发朋友圈或同事群", "cyan"))
    except OSError:
        print(c("  ⚠️ 当前目录不可写，跳过 HTML 生成（终端卡片仍可用）", "yellow"))
    print()
