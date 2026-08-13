#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用途：暗号/预订码签名闭环的单元测试——验证签名防伪 + 跨年 + 有效期。"""
import datetime

import codes

SECRET = "test-secret-key"
PREFIXES = ["STEAM", "ZHENG", "原味", "锁鲜", "蛇口"]


def test_generate_and_verify_valid():
    code = codes.generate_code("2026-08-05", SECRET, PREFIXES)
    ok, msg = codes.verify_code(code, SECRET, PREFIXES, today=datetime.date(2026, 8, 5))
    assert ok, msg


def test_forged_digits_rejected():
    code = codes.generate_code("2026-08-05", SECRET, PREFIXES)
    prefix, mmdd, digits, sig = code.split("-")
    forged_digits = "9999" if digits != "9999" else "0000"
    forged = f"{prefix}-{mmdd}-{forged_digits}-{sig}"
    ok, msg = codes.verify_code(forged, SECRET, PREFIXES, today=datetime.date(2026, 8, 5))
    assert not ok
    assert "签名" in msg


def test_wrong_secret_rejected():
    code = codes.generate_code("2026-08-05", SECRET, PREFIXES)
    ok, _ = codes.verify_code(code, "another-secret", PREFIXES, today=datetime.date(2026, 8, 5))
    assert not ok


def test_expired_rejected():
    code = codes.generate_code("2026-08-05", SECRET, PREFIXES)
    ok, _ = codes.verify_code(code, SECRET, PREFIXES, today=datetime.date(2026, 8, 20))
    assert not ok


def test_cross_year_valid():
    # 12-31 发码，跨年到 1-02 验证应仍有效（修复跨年 bug）
    code = codes.generate_code("2025-12-31", SECRET, PREFIXES)
    ok, msg = codes.verify_code(code, SECRET, PREFIXES, today=datetime.date(2026, 1, 2))
    assert ok, msg


def test_booking_code_cross_year():
    # 12-30 预订次年 1-05，应识别为 CLI 渠道（距到店 6 天）
    code = codes.generate_booking_code("2026-01-05", SECRET)
    ok, msg = codes.verify_booking_code(code, SECRET, today=datetime.date(2025, 12, 30))
    assert ok, msg


def test_booking_code_forged_rejected():
    code = codes.generate_booking_code("2026-01-05", SECRET)
    prefix, mmdd, digits, sig = code.split("-")
    forged = f"{prefix}-{mmdd}-{'9999' if digits != '9999' else '0000'}-{sig}"
    ok, _ = codes.verify_booking_code(forged, SECRET, today=datetime.date(2025, 12, 30))
    assert not ok
