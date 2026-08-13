#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：蒸的好 CLI 极客梗命令（ping / uptime / bench / pr），一行命令输出、截图传播导向。
注册：由 zheng.py 文件末尾 cli.add_command(...) 挂载。
"""
import datetime
import random
import time

import click

from zheng import BRAND, c, banner, divider

ALL_ITEMS = BRAND.all_items


@click.command()
def ping():
    """📡 门店在线检测（码头→餐桌 4 小时 = 延迟梗）"""
    banner()
    print(c("  📡 蛇口渔港 → 万融大厦 · 在线检测", "bold"))
    divider()
    seq = [
        ("64 bytes from 渔港码头: icmp_seq=1 ttl=11 time=4.0h", "渔船刚靠岸"),
        ("64 bytes from 渔港码头: icmp_seq=2 ttl=11 time=4.0h", "师傅在挑货"),
        ("64 bytes from 渔港码头: icmp_seq=3 ttl=11 time=3.8h", "入缸，还在动"),
        ("64 bytes from 餐桌上桌: icmp_seq=4 ttl=11 time=4.1h", "蒸汽锅已预热"),
    ]
    for line, note in seq:
        print(c(f"  {line}", "white"))
        print(c(f"    └─ {note}", "cyan"))
        time.sleep(0.4)
    print()
    print(c("  --- 蛇口渔港 ping statistics（延迟统计）---", "cyan"))
    print(c("  4 packets transmitted, 4 received, 0% loss（4次送达 · 0丢失）", "white"))
    print(c("  这不是延迟，是海的新鲜度。今天也准时到店。", "yellow"))
    print()


@click.command()
def uptime():
    """⏱ 品牌运行时长（2015 年至今，0 事故）"""
    banner()
    start = datetime.date(int(BRAND.established), 1, 1)
    days = (datetime.date.today() - start).days
    years = days // 365
    print(c("  ⏱  uptime", "bold"))
    divider()
    print(c("  ⏱  uptime = 系统在线时长 · 这里是门店开业至今", "cyan"))
    print(c(f"  user: {BRAND.name}", "white"))
    print(c(f"  up {years} years, {days} days（在线：{years}年0事故）", "green"))
    print(c("  load average: 0.00, 0.00, 0.00（客流量：厨房不排队）", "cyan"))
    print(c("  last login: 10:00（开门时间）· 服务从未中断", "white"))
    print()


@click.command()
@click.option("--rounds", "-r", default=3, type=click.IntRange(1, 10), help="基准轮数")
def bench(rounds):
    """⚡ 下单速度基准测试（纯娱乐，不是真下单）"""
    banner()
    print(c("  ⚡ zheng bench — 你的下单速度基准", "bold"))
    divider()
    hot_items = [i for cat in BRAND.menu.values() for i in cat if i.get("hot") and i["price"] is not None]
    total = 0.0
    for i in range(1, rounds + 1):
        t0 = time.perf_counter()
        time.sleep(0.05 + random.random() * 0.05)
        elapsed = time.perf_counter() - t0
        total += elapsed
        item = random.choice(hot_items)
        print(c(f"  [run {i}] 点「{item['name']}」 ¥{item['price']} → {elapsed*1000:.0f} ms", "white"))
    avg = total / rounds
    print(c(f"\n  avg: {avg*1000:.0f} ms/道", "green"))
    if avg < 0.1:
        grade = "SSS — 比蒸汽锅还快，建议来店里当水台"
    elif avg < 0.15:
        grade = "S — 手速在线，适合蒸汽开背大虾"
    else:
        grade = "A — 正常人类速度，点评4.8分等着你"
    print(c(f"  评级：{grade}", "yellow"))
    print(c("  ⚠️  这是基准测试不是真下单，真下单到店点餐", "cyan"))
    print()


@click.command()
@click.option("--add", "-a", multiple=True, help="加菜编号，可多个")
@click.option("--message", "-m", default="今晚想吃", help="commit message")
def pr(add, message):
    """🔀 像提 PR 一样点菜（commit → review → merge → deploy）"""
    banner()
    print(c("  🔀 点菜 PR 流程", "bold"))
    divider()
    items = []
    for code_ in add:
        code_ = code_.upper()
        if code_ not in ALL_ITEMS:
            print(c(f"  ❌ 未知菜品 {code_}", "red"))
            return
        items.append(ALL_ITEMS[code_])
    if not items:
        print(c("  ⚠️ 用法：zheng pr -a A01 -a B02 -m '加班完想吃'", "yellow"))
        return
    total = sum(i["price"] or 0 for i in items)
    print(c("  step 1/4  add files（加菜）", "white"))
    for it in items:
        p = f"¥{it['price']}" if it["price"] is not None else "时价"
        print(c(f"    + {it['name']}  {p}", "green"))
    print(c("  step 2/4  commit（提交）", "white"))
    print(c(f"    [{message}] {len(items)} 道菜 · {total} 行代码（元）", "green"))
    print(c("  step 3/4  code review（评审）", "white"))
    comments = [
        "LGTM ✅ 这道菜没有 bug",
        "⚠️ 东星斑建议蒸 90 秒，别 over-cook",
        "nit: 蒜蓉可以少放点",
        "🙆 approve —— 好吃就是通过",
        "🤔 这蟹没 lint 过，先蒸再说",
    ]
    for _ in range(2):
        print(c(f"    {random.choice(comments)}", "cyan"))
        time.sleep(0.4)
    print(c("  step 4/4  merge → deploy（合并上桌）", "white"))
    print(c("    merged → 厨房 deploy 中，预计 10 分钟上桌", "green"))
    print(c(f"\n  ✅ PR 已 review 通过，到店报菜名即可", "yellow"))
    print(c("  🍽 到店用餐 · 现场结算", "cyan"))
    print()


# 注意：pr 命令不再写本地订单文件（点餐/支付已砍掉，聚焦传播）
