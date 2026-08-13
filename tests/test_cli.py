#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用途：CLI 集成测试——verify 命令正确区分预订码/暗号（防「ZDH 被误判为暗号」回归）。"""
from click.testing import CliRunner

import codes
from zheng import BRAND, cli


def test_verify_cli_recognizes_booking_code():
    secret = BRAND.coupon["secret_key"]
    code = codes.generate_booking_code("2026-08-20", secret)
    result = CliRunner().invoke(cli, ["verify", code])
    assert "渠道预订" in result.output          # 走 booking 分支
    assert "前缀无效" not in result.output       # 防回归：不再被 CODE_RE 误吞
