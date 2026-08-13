#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：蒸的好 CLI 暗号/预订码签名闭环 + 核销后端抽象。
要点：
1. 暗号从「纯随机可穷举」升级为 HMAC 签名码：前缀-MMDD-4位-签名6位。
   商家离线即可验真伪（重算签名比对），伪造/随手编的码直接拒绝。
2. Backend 抽象：默认本地 JSONL 日志（~/.zheng/data/ledger.jsonl），
   未来接飞书/自建后端只需实现 record_issue / record_redeem / stats 三方法。
"""
import base64
import datetime
import hashlib
import hmac
import json
import os
import random
import re
import string

import storage


# ── 签名工具 ────────────────────────────────────────────────

def _sign(body, secret_key):
    """HMAC-SHA256 → base32 前 6 位（大写、去 padding）"""
    digest = hmac.new(secret_key.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    return base64.b32encode(digest).decode("ascii").rstrip("=")[:6]


def _resolve_recent_date(mmdd, today):
    """把 MMDD 解析成「离今天最近的那一天」，正确处理跨年。
    例：今天 01-02、码是 12-31 → 解析为去年 12-31（差 2 天）而非今年 12-31（未来）。"""
    month, day = int(mmdd[:2]), int(mmdd[2:])
    candidates = []
    for year in (today.year, today.year - 1):
        try:
            candidates.append(datetime.date(year, month, day))
        except ValueError:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda d: abs((today - d).days))
    return candidates[0]


# ── 暗号（优惠券，7 天有效）─────────────────────────────────

CODE_RE = re.compile(r"^([A-Z一-鿿]+)-(\d{4})-(\d{4})-([A-Z2-7]{6})$")


def generate_code(date_str, secret_key, prefixes):
    """生成签名暗号：前缀-MMDD-4位-签名"""
    prefix = random.choice(prefixes)
    d = date_str or datetime.date.today().isoformat()
    mmdd = d[5:7] + d[8:10]
    digits = "".join(random.choices(string.digits, k=4))
    body = f"{prefix}-{mmdd}-{digits}"
    return f"{body}-{_sign(body, secret_key)}"


def verify_code(code, secret_key, prefixes, valid_days=7, today=None):
    """独立验证暗号：返回 (是否有效, 说明)。商家端无需网络/数据库即可验真伪。
    today 参数仅用于测试注入日期，缺省为真实今天。"""
    today = today or datetime.date.today()
    code = (code or "").strip().upper()
    m = CODE_RE.match(code)
    if not m:
        return False, "格式无效，应为 前缀-日期-4位-签名（如 STEAM-0805-1234-A1B2C3）"
    prefix, mmdd, digits, sig = m.groups()
    if prefix not in [p.upper() for p in prefixes]:
        return False, f"前缀无效（{prefix}）"
    body = f"{prefix}-{mmdd}-{digits}"
    if not hmac.compare_digest(sig, _sign(body, secret_key)):
        return False, "签名无效（伪造或非法暗号）"
    issue = _resolve_recent_date(mmdd, today)
    if issue is None:
        return False, "日期段无效"
    diff = (today - issue).days
    if diff < 0:
        return False, f"暗号日期 {mmdd} 在未来，无效"
    if diff > valid_days:
        return False, f"已过期（生成于 {mmdd}，超过 {valid_days} 天）"
    remain = valid_days - diff
    return True, f"有效（生成于 {mmdd}，剩 {remain} 天）"


# ── CLI 预订码（渠道识别，到店日 0-30 天）────────────────────

BOOKING_CODE_RE = re.compile(r"^(ZDH)-(\d{4})-(\d{4})-([A-Z2-7]{6})$")


def generate_booking_code(date_str, secret_key):
    """生成 CLI 预订码：ZDH-日期段-4位-签名（餐厅端可验渠道来源）"""
    d = date_str or datetime.date.today().isoformat()
    mmdd = d[5:7] + d[8:10]
    digits = "".join(random.choices(string.digits, k=4))
    body = f"ZDH-{mmdd}-{digits}"
    return f"{body}-{_sign(body, secret_key)}"


def verify_booking_code(code, secret_key, today=None):
    """验证 CLI 预订码。到店日应在今天及之后 30 天内（支持跨年预订）。
    today 参数仅用于测试注入日期。"""
    today = today or datetime.date.today()
    code = (code or "").strip().upper()
    m = BOOKING_CODE_RE.match(code)
    if not m:
        return False, "格式无效，应为 ZDH-0801-1234-XXXXXX"
    _, mmdd, digits, sig = m.groups()
    body = f"ZDH-{mmdd}-{digits}"
    if not hmac.compare_digest(sig, _sign(body, secret_key)):
        return False, "签名无效（伪造或非法预订码）"
    month, day = int(mmdd[:2]), int(mmdd[2:])
    candidates = []
    for year in (today.year, today.year + 1):
        try:
            candidates.append(datetime.date(year, month, day))
        except ValueError:
            continue
    future = [c for c in candidates if c >= today]
    if not future:
        return False, f"预订日期 {mmdd} 已过（只能订今天及以后）"
    d = min(future)
    diff = (d - today).days
    if diff > 30:
        return False, f"预订日期 {mmdd} 超出 30 天，建议直接致电预订"
    return True, f"CLI 渠道预订 · 日期 {mmdd} · 距到店 {diff} 天"


# ── 核销后端（数据闭环）─────────────────────────────────────

class Backend:
    """核销后端抽象。默认 LocalFileBackend；接飞书/自建时实现三方法即可。"""

    def record_issue(self, code, meta=None):
        raise NotImplementedError

    def record_redeem(self, code, ok, meta=None):
        raise NotImplementedError

    def stats(self):
        raise NotImplementedError


class LocalFileBackend(Backend):
    """默认实现：写 JSONL 日志（一行一个事件），可随时导出统计。"""

    def __init__(self, path=None):
        self.path = path or storage.ledger_path()

    def _append(self, entry):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def record_issue(self, code, meta=None):
        self._append({"event": "issue", "code": code,
                      "ts": datetime.datetime.now().isoformat(), "meta": meta or {}})

    def record_redeem(self, code, ok, meta=None):
        self._append({"event": "redeem", "code": code, "ok": bool(ok),
                      "ts": datetime.datetime.now().isoformat(), "meta": meta or {}})

    def stats(self):
        """统计：发码数 / 有效核销数（30 天后可回答「有没有用」）"""
        issued = 0
        redeemed = 0
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if e.get("event") == "issue":
                        issued += 1
                    elif e.get("event") == "redeem" and e.get("ok"):
                        redeemed += 1
        return {"issued": issued, "redeemed": redeemed}
