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


# ── 专属会员码（长期有效，不限次数，鼓励回头客）─────────────

def test_member_code_valid_and_reusable():
    # 会员码不锁次数：同一天反复核销都有效
    code = codes.generate_member_code("2026-08-26", SECRET, PREFIXES)
    for _ in range(3):
        ok, msg = codes.verify_member_code(code, SECRET, PREFIXES, today=datetime.date(2026, 8, 26))
        assert ok, msg


def test_member_code_forged_rejected():
    code = codes.generate_member_code("2026-08-26", SECRET, PREFIXES)
    prefix, ymd, digits, sig = code.split("-")
    forged = f"{prefix}-{ymd}-{'9999' if digits != '9999' else '0000'}-{sig}"
    ok, _ = codes.verify_member_code(forged, SECRET, PREFIXES, today=datetime.date(2026, 8, 26))
    assert not ok


def test_member_code_expired_after_year():
    # 365 天有效：364 天可验，366 天过期
    code = codes.generate_member_code("2026-08-26", SECRET, PREFIXES)
    ok_before = codes.verify_member_code(code, SECRET, PREFIXES, today=datetime.date(2027, 8, 25))[0]
    ok_after = codes.verify_member_code(code, SECRET, PREFIXES, today=datetime.date(2027, 8, 27))[0]
    assert ok_before
    assert not ok_after


def test_member_code_future_issue_rejected():
    # 签发日在未来（时钟错乱/伪造）应拒绝
    code = codes.generate_member_code("2026-09-01", SECRET, PREFIXES)
    ok, _ = codes.verify_member_code(code, SECRET, PREFIXES, today=datetime.date(2026, 8, 26))
    assert not ok
