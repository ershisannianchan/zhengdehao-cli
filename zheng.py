#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：蒸的好 CLI 主框架——品牌无关的命令 / 导航 / 交互 / banner。
品牌数据从 brand.yaml 加载（brand.py），暗号签名闭环在 codes.py，持久化在 storage.py。
换客户 = 换一份 brand.yaml，本文件零改动（即「售卖下一个客户」的入口）。
"""
import datetime
import os
import random
import re
import subprocess
import sys
import time
import webbrowser

import click

import brand as _brand
import codes
import storage

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# Windows 老 cmd（GBK 代码页）防 emoji/中文输出崩溃：强制 stdout/stderr 走 UTF-8
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# 品牌配置（模块加载时读 brand.yaml）
BRAND = _brand.load_brand()
DIANPING_SHOP_URL = BRAND.dianping_url

IN_INTERACTIVE = False  # 交互模式标记
zheng_ai = None         # 扩展模块占位，文件末尾 import 后绑定


# ============================================================
# 管道检测 + ANSI 颜色
# ============================================================

def is_pipe():
    """检测是否被管道，是则自动去色"""
    return not sys.stdout.isatty()


def c(text, color):
    if is_pipe():
        return text
    colors = {
        "red":    "\033[91m", "green":  "\033[92m", "yellow": "\033[93m",
        "blue":   "\033[94m", "purple": "\033[95m", "cyan":   "\033[96m",
        "white":  "\033[97m", "bold":   "\033[1m",  "reset":  "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def pad(s, width):
    """按显示宽度（中文算2列）左对齐补空格，保证终端边框对齐"""
    w = sum(2 if ord(ch) > 0x2E80 else 1 for ch in s)
    return s + " " * max(0, width - w)


def banner():
    """品牌启动页 · 全部文案来自 brand.yaml"""
    if IN_INTERACTIVE:
        return
    b = BRAND.brand
    quote = random.choice(BRAND.quotes) if BRAND.quotes else {"zh": "", "en": ""}
    fresh = random.choice(BRAND.fresh_choices) if BRAND.fresh_choices else ""
    fresh_label = b.get("fresh_label", "今日直采到店")
    print(c(f"""
╔══════════════════════════════════════════════════╗
║                                                  ║
║   {b.get('name', '')}  ·  {b.get('sub_name', '')}
║   Established {b.get('established', '')} · {b.get('tagline', '')} · {b.get('uptime_years', '')}y uptime
║                                                  ║
║   "{b.get('banner_quote', '')}"
║   {b.get('banner_rule', '')}
║                                                  ║
║   {fresh_label}：🔥 {fresh}
║                                                  ║
╚══════════════════════════════════════════════════╝
""", "cyan"))
    print(c("  " + quote.get("zh", ""), "white"))
    print(c("  " + quote.get("en", ""), "cyan"))
    print()
    print(c("  门店  故事  菜单  预订  优惠  暗号", "yellow"))
    print(c(f"  点评 {BRAND.rating} · {BRAND.uptime_years}年 · 0事故", "green"))
    print()


def divider():
    print(c("─" * 50, "blue"))


# ============================================================
# ASCII 二维码（手机可扫）
# ============================================================

def print_qr(url, label=""):
    """用 qrcode 库生成终端二维码，fallback 到 URL 直显"""
    if HAS_QRCODE:
        qr = qrcode.QRCode(border=2, box_size=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii()
    else:
        print(c(f"\n  🔗 {url}", "cyan"))
        print(c("  (pip install qrcode 可显示扫码图)", "yellow"))
    if label:
        print(c(f"  {label}", "white"))


# ============================================================
# 日期/人数解析
# ============================================================

def _valid_date(y, m, d):
    """校验真实日期（拒绝 00 月、13 月等）"""
    try:
        datetime.date(int(y), int(m), int(d))
        return True
    except ValueError:
        return False


def parse_date(raw):
    """解析日期：8.1 / 8/1 / 801 / 2026-08-01 → YYYY-MM-DD；无效返回 None"""
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 10 and raw[4] == "-":
        y, m, d = raw.split("-")
        return raw if _valid_date(y, m, d) else None
    for sep in [".", "/", "。"]:
        raw = raw.replace(sep, "-")
    if raw.isdigit() and len(raw) <= 4:
        raw = raw.zfill(4)
        raw = raw[:2] + "-" + raw[2:]
    parts = raw.split("-")
    year = str(datetime.date.today().year)
    if len(parts) == 2:
        m, d = parts[0].zfill(2), parts[1].zfill(2)
        return f"{year}-{m}-{d}" if _valid_date(year, m, d) else None
    if len(parts) == 3 and len(parts[0]) == 4:
        y, m, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
        return f"{y}-{m}-{d}" if _valid_date(y, m, d) else None
    return None


def parse_persons(raw):
    """解析人数：8 / 8人 / 8 人 / 8位 → int；无数字返回 None"""
    if raw is None:
        return None
    m = re.search(r"\d+", str(raw).strip())
    return int(m.group()) if m else None


# ============================================================
# 数据访问（统一走 storage；订单/桌位/暗号/核销日志全落 ~/.zheng/）
# ============================================================

def load_orders():
    return storage.load_json(storage.orders_path())


def save_orders(orders):
    return storage.save_json(orders, storage.orders_path())


def build_image_map():
    """扫描 assets/dishes，用菜名最长匹配文件名，运行时生成 {菜名: 文件名}。
    客户放图即自动关联（📷 标记 + zheng img），无需手工维护 image_map.json。"""
    dishes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "dishes")
    mapping = {}
    if not os.path.isdir(dishes_dir):
        return mapping
    files = [f for f in os.listdir(dishes_dir)
             if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    items = sorted(BRAND.all_items.values(), key=lambda i: len(i["name"]), reverse=True)
    for f in files:
        stem = os.path.splitext(f)[0]
        for it in items:
            if it["name"] in stem:
                mapping[it["name"]] = f
                break
    return mapping


IMAGE_MAP = build_image_map()

# 核销后端（默认本地 JSONL 日志）
BACKEND = codes.LocalFileBackend()


def generate_booking_code(date_str=None):
    return codes.generate_booking_code(date_str, BRAND.secret_key)


def verify_code(secret):
    return codes.verify_code(secret, BRAND.secret_key,
                             BRAND.coupon.get("prefix", []),
                             BRAND.coupon.get("valid_days", 7))


def verify_booking_code(secret):
    return codes.verify_booking_code(secret, BRAND.secret_key)


def generate_member_code(date_str=None):
    return codes.generate_member_code(date_str, BRAND.secret_key, BRAND.coupon.get("prefix", []))


def verify_member_code(secret):
    return codes.verify_member_code(secret, BRAND.secret_key,
                                    BRAND.coupon.get("prefix", []),
                                    BRAND.coupon.get("member_valid_days", 365))


def get_or_create_member_code():
    """取当前专属会员码；没有则生成、存 config、记一次 issue。code/share 共用，保证同一码。"""
    cfg = storage.load_config()
    code = cfg.get("member_code")
    if not code:
        if not BRAND.secret_key:
            return None  # 未配置密钥，拒绝发码（避免空密钥签发可伪造的码）
        code = generate_member_code()
        cfg["member_code"] = code
        storage.save_config(cfg)
        BACKEND.record_issue(code, {"channel": "code"})
    return code


# ============================================================
# 桌位系统：按日期+时段占用
# ============================================================

def load_tables():
    """读取桌位占用。新格式 { "2026-08-01": { "T01": ["18:30"] } }
    旧格式视为脏数据 → 备份后作废重置"""
    saved = storage.load_json(storage.tables_path(), None)
    if not saved:
        return {}
    first = next(iter(saved)) if isinstance(saved, dict) else ""
    if not (len(first) == 10 and first[4] == "-"):
        try:
            os.replace(storage.tables_path(), storage.tables_path() + ".bak")
        except OSError:
            pass
        return {}
    return saved


def save_tables(tables_state):
    return storage.save_json(tables_state, storage.tables_path())


def occupied_slots(state, date_str, tid):
    return state.get(date_str, {}).get(tid, [])


def table_available(state, date_str, slot, tid, tables):
    if tid not in tables:
        return False
    if not tables[tid].get("available", True):
        return False
    return slot not in occupied_slots(state, date_str, tid)


def find_table(state, date_str, slot, persons, table_type, tables):
    """找可用桌位：最小够用优先；返回 (tid, table) 或 None"""
    suitable = []
    for tid, t in tables.items():
        if t["seats"] >= persons and table_available(state, date_str, slot, tid, tables):
            if table_type == "大厅" and "大厅" not in t["name"]:
                continue
            if table_type == "包厢" and "包厢" not in t["name"]:
                continue
            suitable.append((tid, t))
    suitable.sort(key=lambda x: x[1]["seats"])
    return suitable[0] if suitable else None


def occupy_table(state, date_str, slot, tid):
    state.setdefault(date_str, {}).setdefault(tid, []).append(slot)
    save_tables(state)


def release_table(state, date_str, slot, tid):
    if not tid:
        return False
    day = state.get(date_str)
    if day and tid in day:
        if slot in day[tid]:
            day[tid].remove(slot)
        if not day[tid]:
            del day[tid]
        save_tables(state)
        return True
    return False


def gen_order_id():
    orders = load_orders()
    for _ in range(100):
        oid = "ZDH" + datetime.datetime.now().strftime("%m%d%H%M%S") + "".join(
            random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        if oid not in orders:
            return oid
    return "ZDH" + datetime.datetime.now().strftime("%m%d%H%M%S%f")[:16]


# ============================================================
# AI 离线问答（未配置 api_key 时降级）
# ============================================================

def ai_answer(question):
    q = question.lower()

    if any(w in q for w in ["多少钱", "价格", "人均", "贵不贵", "费用", "便宜", "实惠", "性价比"]):
        return ("💰 人均视点菜而定：凉菜主食人均可百元内，点海鲜/燕鲍参翅则更高\n"
                "💡 输入 优惠 查看大众点评实时套餐和代金券")

    if any(w in q for w in ["推荐", "好吃", "必点", "招牌", "特色"]):
        hot = [i for i in BRAND.hot_items if i.get("price") is not None][:4]
        lines = ["🦞 招牌推荐："]
        for i, it in enumerate(hot, 1):
            lines.append(f"{i}. {it['name']}（¥{it['price']}/{it['unit']}）")
        lines.append("💡 zheng menu 查看完整菜单")
        return "\n".join(lines)

    if any(w in q for w in ["预订", "订位", "包厢", "订桌", "几人", "包间", "几桌"]):
        return ("📅 预订：zheng book [人数]\n"
                "• 2-4人：大厅桌位\n"
                "• 8-20人：包厢\n"
                "💡 包厢有WiFi有插座，程序员友好")

    if any(w in q for w in ["停车", "地址", "在哪", "怎么去", "位置", "地铁"]):
        return (f"📍 {BRAND.address}\n"
                f"🚇 {BRAND.metro}\n"
                f"🅿️  {BRAND.parking}\n"
                f"📞 {BRAND.phone}")

    if any(w in q for w in ["几点", "时间", "营业", "关门", "开门"]):
        return f"🕐 {BRAND.hours}"

    if any(w in q for w in ["团建", "公司", "聚餐", "年会", "活动"]):
        return ("🎉 企业团建：最大包厢可容纳20人，支持对公付款开发票\n"
                "工作日团建额外9折\n"
                f"📞 {BRAND.phone}")

    if any(w in q for w in ["茶水", "服务费", "米饭", "粥底", "收费"]):
        return ("🍚 茶水费：包房10元/位 · 大厅6元/位\n"
                "🍚 米饭5元/碗 · 粥底（白粥/杂粮/排骨）28-38元/份\n"
                "💡 更多详情 zheng info")

    if any(w in q for w in ["蒸汽", "技术", "为什么蒸", "健康", "原味"]):
        return ("🌿 蒸汽锁鲜：102°C恒温 · 92%游离氨基酸保留\n"
                "无油无烟 · 均匀受热 · 开盖仪式感\n"
                "——最简单的方式，最完整的味道。")

    return (f"🤖 关于「{question}」\n"
            "我可以帮你：菜品推荐 · 价格套餐 · 预订包厢 · 门店信息 · 团建方案\n"
            "zheng menu 菜单 | zheng book [人数] 预订 | zheng deals 点评优惠")


# ============================================================
# CLI 命令
# ============================================================

NAV_CMD = {
    "门店": "info", "故事": "story", "菜单": "menu",
    "预订": "book", "优惠": "deals", "暗号": "code", "看图": "view",
}


def run_cmd(line):
    """交互模式执行一行命令：支持 zheng 前缀 / 中文导航词 / 完整参数"""
    tokens = line.split()
    if not tokens:
        return
    first = tokens[0]
    if first in ("zheng", "蒸的好"):
        tokens = tokens[1:]
        if not tokens:
            print(c("  试试：zheng menu / zheng book 4 / zheng code", "cyan"))
            return
        first = tokens[0]
    if first in NAV_CMD:
        tokens[0] = NAV_CMD[first]
    elif first.startswith("看") and len(first) > 1:
        tokens = ["menu", "-c", first[1:]]
    try:
        cli.main(args=tokens, standalone_mode=False)
    except click.NoSuchCommand as e:
        print(c(f"  没有「{e.cmd_name}」命令。可用：菜单 / 预订 / 优惠 / 暗号 / 门店", "yellow"))
    except click.ClickException as e:
        print(c(f"  ❌ {e.format_message()}", "red"))
    except SystemExit:
        pass
    except Exception as e:
        print(c(f"  ⚠️ {e}", "yellow"))


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """蒸的好海鲜馆 · 蛇口网谷 · Steam is the sauce."""
    if ctx.invoked_subcommand is None:
        banner()
        print(c("  门店  故事  菜单  预订  优惠  暗号", "cyan"))
        print(c("  也支持完整命令：menu --hot / book 4 / code --share", "cyan"))
        print(c("  输入 exit 或 q 退出", "cyan"))
        global IN_INTERACTIVE
        IN_INTERACTIVE = True
        while True:
            try:
                cmd = click.prompt(c("  ›", "green")).strip()
            except (KeyboardInterrupt, EOFError):
                print(c("\n  再见！🦞\n", "cyan"))
                break
            if cmd in ("exit", "quit", "q", "退出"):
                print(c("  再见！🦞\n", "cyan"))
                break
            run_cmd(cmd)


# ----------------------------------------------------------
# zheng story
# ----------------------------------------------------------
@cli.command()
@click.option("--part", "-p", type=click.Choice(["蒸", "鲜", "味"]), help="指定章节")
def story(part):
    """📖 品牌故事（蒸/鲜/味 三章）"""
    banner()
    print(c("  📖 品牌故事", "bold"))
    divider()

    chapters = list(BRAND.story.keys())
    parts = [part] if part else chapters
    for i, p in enumerate(parts):
        ch_num = chapters.index(p)
        ch_label = "一二三四五六七八九十"[ch_num] if ch_num < 10 else str(ch_num + 1)
        print(c(f"\n  ═══ 第{ch_label}章 · {p} ═══\n", "yellow"))
        for line in BRAND.story[p].strip().split("\n"):
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                print(c(f"  {line}", "cyan"))
            else:
                print(c(f"  {line}", "white"))
        if i < len(parts) - 1:
            time.sleep(0.6)

    print()
    divider()
    print(c("  这个故事没有结尾。因为那口蒸汽锅还在用。", "green"))
    tip = "输入 优惠 → 去点评看看" if IN_INTERACTIVE else "zheng deals → 去点评看看"
    print(c(f"  {tip}", "yellow"))
    print()


# ----------------------------------------------------------
# zheng deals
# ----------------------------------------------------------
@cli.command()
@click.option("--open", "open_browser", is_flag=True, help="直接浏览器打开大众点评")
def deals(open_browser):
    """🎫 扫码去大众点评看套餐&星级&评价"""
    banner()
    print(c("  🎫 大众点评", "bold"))
    divider()

    if open_browser:
        print(c(f"\n  正在打开大众点评...", "cyan"))
        webbrowser.open(DIANPING_SHOP_URL)
        print(c(f"  🔗 {DIANPING_SHOP_URL}", "white"))
        print(c("  📱 手机页面 → 看评分 · 团购 · 代金券 → 直接下单", "yellow"))
        print()
        return

    print(c("\n  扫码直达大众点评店铺页：", "yellow"))
    print(c("  （评分 · 团购套餐 · 代金券 · 用户评价）", "cyan"))
    print()
    print_qr(DIANPING_SHOP_URL, "微信/支付宝扫一扫 → 看评分选套餐 → 下单 → 到店核销")
    print(c(f"\n  🔗 {DIANPING_SHOP_URL}", "cyan"))
    print(c(f"  💡 zheng deals --open  浏览器直接打开", "yellow"))
    print()


# ----------------------------------------------------------
# zheng menu
# ----------------------------------------------------------
@cli.command()
@click.option("--category", "-c", default=None, help="菜品分类（zheng menu -c 凉菜）")
@click.option("--all", "show_all", is_flag=True, help="显示全部菜品")
@click.option("--hot", is_flag=True, help="只看热门（跨分类）")
def menu(category, show_all, hot):
    """🍽️ 查看菜单"""
    banner()
    print(c("  📋 今日菜单  |  " + datetime.datetime.now().strftime("%Y-%m-%d"), "bold"))
    divider()

    def price_str(it):
        return "时价" if it["price"] is None else f"¥{it['price']}/{it['unit']}"

    def img_tag(it):
        return c(" 📷", "cyan") if it["name"] in IMAGE_MAP else ""

    if hot:
        print(c("\n  🔥 招牌热门（跨分类）", "blue"))
        for cat, lst in BRAND.menu.items():
            for it in lst:
                if it.get("hot"):
                    print(f"  {c(it['id'],'yellow')} {c(it['name'],'white')}{img_tag(it)}  {price_str(it)}")
    elif category:
        if category not in BRAND.menu:
            matches = [k for k in BRAND.menu if category in k or k in category]
            category = matches[0] if matches else None
        if not category:
            print(c(f"  ❌ 未找到分类，可用：{' / '.join(BRAND.menu.keys())}", "red"))
            return
        print(c(f"\n  {category}", "blue"))
        for item in BRAND.menu[category]:
            hot_tag = c(" 🔥", "red") if item.get("hot") else "  "
            print(f"  {c(item['id'],'yellow')} {hot_tag} {c(item['name'],'white')}{img_tag(item)}  {price_str(item)}")
    elif show_all:
        for cat, lst in BRAND.menu.items():
            print(c(f"\n  {cat}", "blue"))
            for item in lst:
                hot_tag = c(" 🔥", "red") if item.get("hot") else "  "
                print(f"  {c(item['id'],'yellow')} {hot_tag} {c(item['name'],'white')}{img_tag(item)}  {price_str(item)}")
    else:
        print(c("\n  🗂  分类导航", "cyan"))
        for cat, lst in BRAND.menu.items():
            n = len(lst)
            n_hot = sum(1 for i in lst if i.get("hot"))
            n_img = sum(1 for i in lst if i["name"] in IMAGE_MAP)
            extra = (f" · {n_hot}🔥" if n_hot else "") + (f" · {n_img}📷" if n_img else "")
            print(f"  {c(cat,'blue')}  {n} 道{extra}")
        print(c("\n  💡 用法：", "cyan"))
        print(c("    看凉菜（看+分类名）  只看某个分类", "white"))
        print(c("    zheng menu --hot    招牌热门", "white"))
        print(c("    zheng menu --all    全部菜品", "white"))
        print(c("    到店点餐 · zheng book [人数] 预订座位", "white"))

    print()

    if category:
        return

    divider()
    print(c("\n  📱 扫码看评价 · 买套餐 · 在线预订\n", "yellow"))
    print_qr(DIANPING_SHOP_URL, "微信/支付宝扫一扫 → 看评分选套餐 → 下单 → 到店核销")
    print(c(f"  🔗 {DIANPING_SHOP_URL}", "cyan"))

    print()
    tip = "输入 暗号" if IN_INTERACTIVE else "zheng code"
    print(c(f"  🔐 想领 8 折会员码 → {tip}（长期有效 · 不限次数）", "yellow"))

    print()
    print(c("  ╔══════════════════════════════════════════╗", "yellow"))
    print(c("  ║  📸 截屏本页 → 到店出示 → 赠招牌蒸汽海鲜  ║", "yellow"))
    print(c("  ╚══════════════════════════════════════════╝", "yellow"))

    print()
    tip = "输入 预订" if IN_INTERACTIVE else "zheng book [人数] 预订"
    print(c(f"  {tip}", "yellow"))
    print()


# ----------------------------------------------------------
# zheng book
# ----------------------------------------------------------
@cli.command()
@click.argument("persons_arg", required=False)
@click.option("--date", "-d", default=None, help="日期 YYYY-MM-DD（默认今天）")
@click.option("--time", "-t", "booking_time", default=None, help="时间 HH:MM")
@click.option("--persons", "-n", default=None, help="人数（如 8 / 8人）")
@click.option("--type", "-y", "table_type", default=None, help="大厅/包厢/不限")
@click.option("--name", "-m", default=None, help="预订人")
@click.option("--phone", "-p", default=None, help="电话")
def book(date, booking_time, persons_arg, persons, table_type, name, phone):
    """📅 预订桌位"""
    banner()
    print(c("  📅 预订桌位", "bold"))
    divider()

    today_str = datetime.date.today().isoformat()

    if date:
        parsed = parse_date(date)
        if not parsed:
            print(c("  ❌ 日期格式无效，试试 8.1 / 8/1 / 801 / 2026-08-01", "red"))
            return
        date = parsed
    else:
        while True:
            raw = click.prompt(c("  日期", "yellow"), default=today_str, show_default=True)
            parsed = parse_date(raw)
            if parsed:
                date = parsed
                break
            print(c("  ❌ 日期格式无效，试试 8.1 / 8/1 / 801 / 2026-08-01", "red"))
    print(c(f"  📅 {date}", "white"))

    SLOTS = ["11:00", "11:30", "12:00", "12:30", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00"]
    if booking_time:
        booking_time = booking_time.replace("：", ":").replace("∶", ":")
        if booking_time not in SLOTS:
            print(c(f"  ❌ 可选时段：{', '.join(SLOTS)}", "red"))
            return
    else:
        print(c(f"  时段：{'  '.join(SLOTS[:5])}", "cyan"))
        print(c(f"        {'  '.join(SLOTS[5:])}", "cyan"))
        while True:
            booking_time = click.prompt(c("  时间", "yellow"), default="18:30")
            booking_time = booking_time.replace("：", ":").replace("∶", ":")
            if booking_time in SLOTS:
                break
            print(c(f"  ❌ 可选时段：{', '.join(SLOTS)}", "red"))
    print(c(f"  🕐 {booking_time}", "white"))

    PERSON_OPTIONS = [2, 4, 6, 8, 10, 12, 16, 20]
    persons = persons or persons_arg
    if not persons:
        print(c(f"  {'  '.join(str(p)+'人' for p in PERSON_OPTIONS)}", "cyan"))
        while True:
            raw = click.prompt(c("  人数", "yellow"), default="2")
            persons = parse_persons(raw)
            if persons and (persons in PERSON_OPTIONS or 1 <= persons <= 20):
                break
            print(c(f"  ❌ 请输入 {PERSON_OPTIONS[0]}-{PERSON_OPTIONS[-1]} 的整数人数，如 8 / 8人", "red"))
    else:
        persons = parse_persons(str(persons))
        if not persons or not (1 <= persons <= 20):
            print(c(f"  ❌ 人数无效，请用 1-20 的整数，如 8 / 8人", "red"))
            return
    print(c(f"  👥 {persons}人", "white"))

    TYPE_OPTIONS = ["不限", "大厅", "包厢"]
    if not table_type:
        print(c(f"  {' / '.join(TYPE_OPTIONS)}", "cyan"))
        while True:
            table_type = click.prompt(c("  桌型偏好", "yellow"), default="不限")
            if table_type in TYPE_OPTIONS:
                break
            print(c(f"  ❌ 请选：{' / '.join(TYPE_OPTIONS)}", "red"))
    print(c(f"  🪑 {table_type}", "white"))

    if not name:
        name = click.prompt(c("  预订人", "yellow"))
    if not phone:
        while True:
            phone = click.prompt(c("  电话", "yellow"))
            if phone.isdigit() and len(phone) >= 11:
                break
            print(c("  ❌ 请输入11位手机号", "red"))

    tables_state = load_tables()
    slot = booking_time
    found = find_table(tables_state, date, slot, persons, table_type, BRAND.tables)
    if found:
        selected_id, selected = found
        occupy_table(tables_state, date, slot, selected_id)
    else:
        selected_id, selected = ("AUTO", {"name": f"{table_type}（到店安排）", "seats": persons})

    order_id = gen_order_id()
    booking_code = generate_booking_code(date)
    booking = {
        "order_id": order_id, "type": "booking",
        "table_id": selected_id, "table_name": selected["name"],
        "persons": persons, "name": name, "phone": phone,
        "time": booking_time, "date": date,
        "preference": table_type,
        "source": "cli", "booking_code": booking_code,
        "status": "confirmed", "created_at": datetime.datetime.now().isoformat()
    }

    orders = load_orders()
    orders[order_id] = booking
    save_orders(orders)

    divider()
    print(c(f"\n  ✅ 预订成功", "green"))
    divider()
    print(c(f"  📅 {date}  🕐 {booking_time}  👥 {persons}人  🪑 {table_type}", "white"))
    print(c(f"  {selected['name']}", "cyan"))
    print(c(f"  订单号：{order_id}", "yellow"))
    print(c(f"  🔖 CLI 预订码：{booking_code}", "yellow"))
    print(c(f"  预订人：{name}  📞 {phone}", "white"))
    print(c(f"\n  📞 致电门店报预订码 → 门店即识别为 CLI 渠道（可享专属权益）", "cyan"))
    print(c(f"  📱 门店将在10分钟内致电确认", "cyan"))
    print()


# ----------------------------------------------------------
# zheng cancel
# ----------------------------------------------------------
@cli.command()
@click.argument("order_id")
def cancel(order_id):
    """❌ 取消订单并释放桌位"""
    banner()
    print(c("  ❌ 取消订单", "bold"))
    divider()

    order_id = order_id.upper()
    orders = load_orders()
    if order_id not in orders:
        print(c(f"\n  ❌ 未找到订单 {order_id}", "red"))
        return

    od = orders[order_id]
    if od.get("status") == "cancelled":
        print(c(f"\n  ⚠️ 订单 {order_id} 已取消过", "yellow"))
        return

    if od.get("type") == "booking" and od.get("table_id") and od.get("table_id") != "AUTO":
        released = release_table(load_tables(), od.get("date"), od.get("time"), od.get("table_id"))
        table_note = f"  🪑 {od.get('table_name')} 已释放" if released else "  🪑 桌位记录未找到，未释放"
    else:
        table_note = ""

    orders[order_id]["status"] = "cancelled"
    orders[order_id]["cancelled_at"] = datetime.datetime.now().isoformat()
    save_orders(orders)

    print(c(f"\n  ✅ 订单 {order_id} 已取消", "green"))
    if table_note:
        print(c(table_note, "cyan"))
    print()


# ----------------------------------------------------------
# zheng status
# ----------------------------------------------------------
@cli.command()
@click.argument("order_id", required=False)
def status(order_id):
    """📦 查看订单状态"""
    banner()
    orders = load_orders()

    if not orders:
        print(c("  暂无订单", "yellow"))
        return

    status_map = {
        "confirmed":       c("✅ 已确认", "green"),
        "pending_payment": c("⏳ 待支付", "yellow"),
        "paid":            c("💳 已支付", "green"),
        "cancelled":       c("❌ 已取消", "red"),
    }

    if order_id:
        order_id = order_id.upper()
        if order_id not in orders:
            print(c(f"  ❌ 未找到 {order_id}", "red"))
            return
        display = {order_id: orders[order_id]}
    else:
        display = orders

    print(c("  📦 订单", "bold"))
    divider()

    for oid, od in display.items():
        st = status_map.get(od.get("status", ""), od.get("status", ""))
        print(c(f"\n  订单号：{oid}", "yellow"))
        print(f"  类型：{'预订' if od.get('type') == 'booking' else '点餐'}  状态：{st}")
        if od.get("type") == "booking":
            print(c(f"  {od.get('table_name')} · {od.get('persons')}人 · {od.get('time')}", "white"))
            print(c(f"  {od.get('name')} · {od.get('phone')}", "white"))
            if od.get("booking_code"):
                print(c(f"  🔖 {od.get('booking_code')}（CLI 渠道）", "cyan"))
        print(c(f"  {od.get('created_at','')[:16]}", "cyan"))
    divider()
    print()


# ----------------------------------------------------------
# zheng info
# ----------------------------------------------------------
@cli.command()
def info():
    """📍 门店信息"""
    banner()
    print(c("  📍 门店信息", "bold"))
    divider()
    for label, val in BRAND.info_items:
        print(c(f"  {label}：", "yellow") + c(val, "white"))
    print()
    rooms_ok = os.path.exists(ASSETS["rooms"]["path"])
    dishes_ok = os.path.exists(ASSETS["dishes"]["path"])
    video_ok = os.path.exists(ASSETS["video"]["path"])
    if rooms_ok:
        n = len([f for f in os.listdir(ASSETS["rooms"]["path"]) if f.lower().endswith((".png", ".jpg", ".jpeg"))])
        tip = "输入 view rooms → 浏览全部" if IN_INTERACTIVE else "蒸的好看图 rooms → 浏览全部"
        print(c(f"  📷 包厢实拍（{n}张）→ {tip}", "cyan"))
    if dishes_ok:
        n = len([f for f in os.listdir(ASSETS["dishes"]["path"]) if f.lower().endswith((".png", ".jpg", ".jpeg"))])
        tip = "输入 view dishes → 浏览全部" if IN_INTERACTIVE else "蒸的好看图 dishes → 浏览全部"
        print(c(f"  📷 菜品实拍（{n}张）→ {tip}", "cyan"))
    if video_ok:
        tip = "输入 view video → 播放" if IN_INTERACTIVE else "蒸的好看图 video → 播放"
        print(c(f"  🎬 品牌短片 → {tip}", "cyan"))
    print()


# ----------------------------------------------------------
# 本地资源查看
# ----------------------------------------------------------

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ASSETS = {
    "rooms":  {"path": os.path.join(ASSETS_DIR, "rooms"),  "name": "包厢实拍", "type": "dir"},
    "dishes": {"path": os.path.join(ASSETS_DIR, "dishes"), "name": "菜品实拍", "type": "dir"},
    "video":  {"path": os.path.join(ASSETS_DIR, "brand.mp4"), "name": "品牌短片", "type": "file"},
}


@cli.command()
@click.argument("target", required=False)
def view(target):
    """📷 查看包厢/菜品/视频（zheng view rooms）"""
    banner()

    if not target:
        print(c("  📷 本地资源", "bold"))
        divider()
        for key, a in ASSETS.items():
            exists = os.path.exists(a["path"])
            status = c("✓", "green") if exists else c("✗ 未添加", "red")
            count = ""
            if exists and a["type"] == "dir":
                imgs = [f for f in os.listdir(a["path"])
                        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"))]
                count = f"（{len(imgs)}张）"
            if IN_INTERACTIVE:
                print(c(f"  {status}  看图 {key:<8} → {a['name']}{count}", "white"))
            else:
                print(c(f"  {status}  蒸的好看图 {key:<8} → {a['name']}{count}", "white"))
        print()
        if IN_INTERACTIVE:
            print(c("  输入：看图 rooms / 看图 dishes / 看图 video", "cyan"))
        else:
            print(c("  蒸的好看图 rooms / dishes / video", "cyan"))
        print()
        return

    if target not in ASSETS:
        print(c(f"  ❌ 未知资源：{target}", "red"))
        print(c(f"  可用：{' / '.join(ASSETS.keys())}", "yellow"))
        return

    asset = ASSETS[target]
    path = asset["path"]

    if not os.path.exists(path):
        print(c(f"  ❌ {asset['name']}未添加", "red"))
        print(c(f"  请将文件放入：{path}", "yellow"))
        if target == "video":
            print(c(f"  视频文件命名为 brand.mp4", "cyan"))
        else:
            print(c(f"  将照片放入该文件夹即可", "cyan"))
        return

    print(c(f"  📷 正在打开{asset['name']}...", "cyan"))

    if asset["type"] == "dir":
        images = [f for f in os.listdir(path)
                  if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"))]
        if images:
            open_file(path)
            print(c(f"  {len(images)} 张照片 · 可左右切换浏览", "white"))
        else:
            open_file(path)
            print(c(f"  空文件夹", "white"))
    else:
        if os.path.exists(path):
            open_file(path)
            print(c(f"  {asset['name']}", "white"))

    print()


@cli.command()
@click.argument("item_id")
def img(item_id):
    """📷 查看菜品图片（zheng img L01，需对应素材）"""
    banner()
    item_id = item_id.upper()
    if item_id not in BRAND.all_items:
        print(c(f"  ❌ 未知菜品 {item_id}", "red"))
        return
    item = BRAND.all_items[item_id]
    fname = IMAGE_MAP.get(item["name"])
    if not fname:
        print(c(f"  📷 {item['name']}（{item_id}）暂无图片素材", "yellow"))
        print(c("  放入 assets/dishes 后运行 zheng img 刷新映射即可关联", "cyan"))
        return
    path = os.path.join(ASSETS_DIR, "dishes", fname)
    if os.path.exists(path):
        try:
            open_file(path)
            print(c(f"  📷 {item['name']}：{fname}", "green"))
        except OSError:
            print(c(f"  🔗 {path}", "cyan"))
    else:
        print(c(f"  ⚠️ 图片文件缺失：{path}", "red"))
    print()


@cli.command()
def dishes():
    """📷 菜品素材盘点（列出照片，辅助核对与菜单一致性）"""
    banner()
    print(c("  📷 菜品素材盘点", "bold"))
    divider()
    path = ASSETS["dishes"]["path"]
    if not os.path.exists(path):
        print(c(f"  ❌ 无菜品照片目录：{path}", "red"))
        return
    files = [f for f in os.listdir(path)
             if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"))]
    print(c(f"  共 {len(files)} 张照片\n", "white"))
    for f in files:
        print(c(f"  · {f}", "white"))
    print()
    print(c("  ⚠️  菜单菜名 vs 照片可能不一致，请人工核对是否本店实拍", "yellow"))
    print()


# ----------------------------------------------------------
# zheng code（专属暗号 · 签名闭环）
# ----------------------------------------------------------
@cli.command()
@click.option("--verify", "-v", default=None, help="验证暗号是否有效（商家端独立可验）")
@click.option("--share", is_flag=True, help="生成分享文案并复制到剪贴板")
def code(verify, share):
    """🎟️ 专属会员码（领一次长期有效，到店报码→全场8折，不限次数）"""
    banner()

    if verify:
        verify = (verify or "").strip().upper()
        ok, msg = verify_member_code(verify)
        kind = "member"
        if not ok and codes.CODE_RE.match(verify):
            ok, msg = verify_code(verify)  # 兼容旧的 7 天暗号
            kind = "coupon"
        print(c("\n  🎟️ 会员码验证", "bold"))
        divider()
        print(c(f"  码：{verify}", "yellow"))
        print(c(f"  状态：{'✅' if ok else '❌'} {msg}", "green" if ok else "red"))
        # 记录核销尝试（数据闭环，kind 区分会员码/暗号）
        BACKEND.record_redeem(verify, ok, {"channel": "verify", "kind": kind})
        print()
        return

    # 专属会员码：首次生成并持久化，之后复用同一个码（鼓励回头客）
    member_code = get_or_create_member_code()
    if not member_code:
        print(c("  ❌ 未配置签名密钥，无法发码", "red"))
        print(c("  💡 请设置 ZHENG_SECRET 环境变量，或写入 ~/.zheng/secret", "yellow"))
        print()
        return

    W = 42

    def _row(text):
        return f"  ║ {pad(text, W)}║"

    discount = BRAND.coupon.get("discount", "全场8折")
    exclude = BRAND.coupon.get("exclude", "")
    print(c("\n  🎟️ 你的专属会员码\n", "bold"))
    print(c("  ╔" + "═" * W + "╗", "yellow"))
    print(c(_row(f"      {member_code}"), "yellow"))
    print(c(_row(""), "yellow"))
    print(c(_row(f"到店报码 → {discount}"), "yellow"))
    print(c(_row(f"（{exclude}）"), "yellow"))
    print(c(_row(f"长期有效 · 不限次数 · 午市晚市都欢迎"), "yellow"))
    print(c("  ╚" + "═" * W + "╝", "yellow"))
    print()
    print(c(f"  💡 商家验证：zheng code --verify {member_code}", "cyan"))
    print(c(f"  📤 分享给同事：zheng code --share", "cyan"))

    if share:
        share_text = (f"🦞 请你的客——「{BRAND.name}」专属会员码：{member_code}\n"
                      f"📍 {BRAND.address} · {BRAND.uptime_years}年 · 点评{BRAND.rating}\n"
                      f"🎟️ 到店报码 → {discount}（{exclude}）· 长期有效不限次数")
        print(c("\n  📤 分享文案：\n", "bold"))
        for line in share_text.split("\n"):
            print(c(f"  {line}", "white"))
        print()
        _copy_to_clipboard(share_text)
    print()


def open_file(path):
    """跨平台打开文件/文件夹：Windows startfile / macOS open / Linux xdg-open"""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])


def _copy_to_clipboard(text):
    """复制文本到剪贴板：Windows(ctypes) / macOS(pbcopy) / Linux(xclip/xsel)"""
    try:
        if sys.platform == "win32":
            import ctypes
            CF_UNICODETEXT = 13
            data = text.encode("utf-16-le") + b"\x00\x00"
            h = ctypes.windll.kernel32.GlobalAlloc(0x0042, len(data))
            p = ctypes.windll.kernel32.GlobalLock(h)
            ctypes.memmove(p, data, len(data))
            ctypes.windll.kernel32.GlobalUnlock(h)
            if not ctypes.windll.user32.OpenClipboard(None):
                raise OSError("open clipboard failed")
            ctypes.windll.user32.EmptyClipboard()
            ctypes.windll.user32.SetClipboardData(CF_UNICODETEXT, h)
            ctypes.windll.user32.CloseClipboard()
        elif sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        else:
            copied = False
            for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
                try:
                    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
                    copied = True
                    break
                except FileNotFoundError:
                    continue
            if not copied:
                print(c("  （未安装 xclip/xsel，请手动复制文案）", "yellow"))
                return
        print(c("  ✅ 已复制到剪贴板", "green"))
    except Exception:
        print(c("  （未能自动复制，请手动选择文案复制）", "yellow"))


# ----------------------------------------------------------
# zheng verify（门店端验证暗号 / CLI 预订码，支持 --file 批量对账）
# ----------------------------------------------------------

# 从登记本自由文本中提取码（会员码 8 位日期 / 暗号·预订码 4 位日期）
CODE_TOKEN_RE = re.compile(r"[A-Z一-鿿]+-\d{4,8}-\d{4}-[A-Z2-7]{6}")


def _verify_one(code_arg):
    """验一把码：返回 (是否有效或 None=无法识别, 类型标签, 说明)，会员码/暗号记核销日志。
    先判预订码（ZDH 前缀更具体），再判会员码（8位签发日）、暗号（4位日期）。"""
    code_arg = code_arg.strip().upper()
    if codes.BOOKING_CODE_RE.match(code_arg):
        ok, msg = verify_booking_code(code_arg)
        return ok, "CLI 预订码", msg
    if codes.MEMBER_CODE_RE.match(code_arg):
        ok, msg = verify_member_code(code_arg)
        BACKEND.record_redeem(code_arg, ok, {"channel": "verify", "kind": "member"})
        return ok, "会员码", msg
    if codes.CODE_RE.match(code_arg):
        ok, msg = verify_code(code_arg)
        BACKEND.record_redeem(code_arg, ok, {"channel": "verify", "kind": "coupon"})
        return ok, "暗号", msg
    return None, "无法识别", "格式不符"


@cli.command()
@click.argument("code_arg", required=False)
@click.option("--file", "-f", "batch_file", default=None,
              help="批量验码：登记本文本文件（从每行自由文本中提取码，事后对账用）")
def verify(code_arg, batch_file):
    """🔍 验证会员码 / 暗号 / CLI 预订码（门店端独立验证渠道）"""
    banner()

    if batch_file:
        if not os.path.exists(batch_file):
            print(c(f"  ❌ 文件不存在：{batch_file}", "red"))
            return
        with open(batch_file, "r", encoding="utf-8") as f:
            found = CODE_TOKEN_RE.findall(f.read().upper())
        if not found:
            print(c("  ❌ 未识别到任何码（格式：前缀-日期-4位-签名）", "red"))
            return
        print(c(f"  🔍 批量验码 · 共识别 {len(found)} 把", "bold"))
        divider()
        ok_n = 0
        for code_i in found:
            ok, label, msg = _verify_one(code_i)
            ok_n += 1 if ok else 0
            print(f"  {'✅' if ok else '❌'} {c(code_i, 'yellow')}  "
                  f"{c(label + ' · ' + msg, 'green' if ok else 'red')}")
        divider()
        print(c(f"  汇总：有效 {ok_n} · 无效 {len(found) - ok_n}", "bold"))
        print()
        return

    if not code_arg:
        print(c("  用法：zheng verify <码>  或  zheng verify --file 登记本.txt", "yellow"))
        print(c("  支持：会员码（STEAM-20260826-1234-XXXXXX）/ 暗号（STEAM-0805-1234-XXXXXX）/ 预订码（ZDH-0801-1234-XXXXXX）", "cyan"))
        return

    ok, label, msg = _verify_one(code_arg)
    if ok is None:
        print(c(f"  ❌ 无法识别：{code_arg}", "red"))
        print(c("  支持：会员码（STEAM-20260826-1234-XXXXXX）/ 暗号（STEAM-0805-1234-XXXXXX）/ 预订码（ZDH-0801-1234-XXXXXX）", "cyan"))
        return
    print(c(f"\n  🔍 {label}验证", "bold"))
    divider()
    print(c(f"  码：{code_arg.strip().upper()}", "yellow"))
    print(c(f"  状态：{'✅' if ok else '❌'} {msg}", "green" if ok else "red"))
    print()


# ----------------------------------------------------------
# zheng stats（数据闭环出口：发码/核销统计）
# ----------------------------------------------------------
@cli.command()
def stats():
    """📊 营销数据：发码 / 核销 / 回头率（会员码数据闭环）"""
    banner()
    print(c("  📊 营销数据", "bold"))
    divider()
    s = BACKEND.stats()
    print(c(f"  发放会员码：{s.get('issued', 0)} 个", "white"))
    print(c(f"  核销总次数：{s.get('redeemed', 0)} 次", "white"))
    print(c(f"  唯一顾客：{s.get('unique', 0)} 人", "white"))
    if s.get("unique"):
        color = "green" if s.get("repeat") else "yellow"
        print(c(f"  回头客：{s.get('repeat', 0)} 人（回头率 {s.get('repeat_rate', 0)*100:.0f}%）", color))
        print(c(f"  回头次数：{s.get('repeat_visits', 0)} 次", "white"))
    else:
        print(c("  回头率：—（暂无核销记录）", "yellow"))
    print()
    print(c("  💡 数据来源：~/.zheng/data/ledger.jsonl（本地核销日志）", "cyan"))
    print(c("  💡 回头率 = 核销过 2 次以上的码占唯一码的比例（会员码可复用）", "cyan"))
    print(c("  💡 口径：发码数只含 CLI 渠道（落地页发码在 Vercel KV）；核销数来自对账时 verify 记录", "cyan"))
    print()


# ----------------------------------------------------------
# zheng config（hidden：AI 配置 api_key / model / nickname）
# ----------------------------------------------------------
@cli.group("config", invoke_without_command=True, hidden=True)
@click.pass_context
def config(ctx):
    """⚙️ 配置（api_key / nickname / model）"""
    if ctx.invoked_subcommand is None:
        banner()
        cfg = storage.load_config()
        print(c("  ⚙️  当前配置", "bold"))
        divider()
        if not cfg:
            print(c("  （空）用 zheng config set <key> <value> 添加", "yellow"))
        for k, v in cfg.items():
            if k == "api_key" and v:
                v = v[:6] + "****" + v[-4:]
            print(c(f"  {k} = {v}", "white"))
        print()
        print(c("  可用项：api_key（DeepSeek）/ model / nickname", "cyan"))
        print()


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    cfg = storage.load_config()
    cfg[key] = value
    storage.save_config(cfg)
    shown = value[:6] + "****" + value[-4:] if key == "api_key" and len(value) > 10 else value
    print(c(f"  ✅ 已设置 {key} = {shown}", "green"))


@config.command("get")
@click.argument("key")
def config_get(key):
    cfg = storage.load_config()
    v = cfg.get(key, "")
    if key == "api_key" and v:
        v = v[:6] + "****" + v[-4:]
    print(c(f"  {key} = {v or '（未设置）'}", "white"))


@config.command("del")
@click.argument("key")
def config_del(key):
    cfg = storage.load_config()
    if key in cfg:
        del cfg[key]
        storage.save_config(cfg)
        print(c(f"  ✅ 已删除 {key}", "green"))
    else:
        print(c(f"  ⚠️ {key} 未设置", "yellow"))


# ----------------------------------------------------------
# zheng ask（hidden：AI 管家，真 AI 优先，否则离线问答）
# ----------------------------------------------------------
def _ask_reply(q):
    content, model = zheng_ai.ask_ai(q) if zheng_ai else (None, "离线模式")
    if content:
        tag = "" if model == "离线模式" else f"[{model}]"
        print(c(f"  管家{tag}：", "purple"))
        for line in content.split("\n"):
            print(c(f"  {line}", "white"))
    else:
        print(c("  管家（离线）：", "purple"))
        for line in ai_answer(q).split("\n"):
            print(c(f"  {line}", "white"))
    print()


@cli.command("ask", hidden=True)
@click.argument("question", nargs=-1)
def ask(question):
    """🤖 AI管家（配置 api_key 后为真 AI，否则离线模式）"""
    banner()
    print(c("  🤖 AI管家", "bold"))
    divider()
    if question:
        q = " ".join(question)
        print(c(f"\n  你：{q}\n", "green"))
        _ask_reply(q)
    else:
        print(c("  可以问我：推荐 · 价格 · 预订 · 地址 · 团建 · 蒸汽技术", "cyan"))
        print(c("  输入 exit 退出\n", "yellow"))
        while True:
            try:
                q = click.prompt(c("  你", "green"))
                if q.lower() in ("exit", "quit", "退出", "再见"):
                    print(c("\n  感谢光临！🦞\n", "cyan"))
                    break
                _ask_reply(q)
            except (KeyboardInterrupt, EOFError):
                print(c("\n\n  感谢光临！\n", "cyan"))
                break


# ----------------------------------------------------------
# 快捷命令分发器
# ----------------------------------------------------------
SHORTCUTS = {
    "蒸的好菜单": ["menu"],
    "蒸的好预订": ["book"],
    "蒸的好地址": ["info"],
    "蒸的好电话": ["info"],
    "蒸的好故事": ["story"],
    "蒸的好优惠": ["deals"],
    "蒸的好暗号": ["code"],
    "蒸的好看图": ["view"],
}


def shortcut():
    name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    if name in SHORTCUTS:
        sys.argv[1:1] = SHORTCUTS[name]
    cli()


# ----------------------------------------------------------
# 扩展模块（真AI / 梗命令 / 分享卡片）— 文件末尾 import 避免循环
# ----------------------------------------------------------
try:
    import zheng_ai
    import zheng_fun
    import zheng_share
    cli.add_command(zheng_fun.ping)
    cli.add_command(zheng_fun.uptime)
    cli.add_command(zheng_fun.bench)
    cli.add_command(zheng_fun.pr)
    cli.add_command(zheng_share.share)
except ImportError as e:
    print(c(f"  ⚠️ 扩展模块加载失败：{e}", "yellow"))


if __name__ == "__main__":
    cli()
