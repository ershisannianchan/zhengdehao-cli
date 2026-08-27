#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用途：CLI 集成测试——verify 命令正确区分预订码/暗号（防「ZDH 被误判为暗号」回归）。"""
import datetime

from click.testing import CliRunner

import codes
from zheng import cli


def test_verify_cli_recognizes_booking_code(monkeypatch):
    # 注入测试密钥：开源后任何人 clone 都能跑，不依赖本机 ~/.zheng/secret
    monkeypatch.setenv("ZHENG_SECRET", "test-secret-key")
    secret = "test-secret-key"
    # 用相对日期，不能写死——预订码要求到店日在今天起 30 天内，
    # 写死的日期会随时间流逝变成过去时间，让测试无故变红。
    arrival = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    code = codes.generate_booking_code(arrival, secret)
    result = CliRunner().invoke(cli, ["verify", code])
    assert "渠道预订" in result.output          # 走 booking 分支
    assert "前缀无效" not in result.output       # 防回归：不再被 CODE_RE 误吞


def test_verify_batch_file(monkeypatch, tmp_path):
    # 批量验码：登记本自由文本中提取码，真假混合时汇总正确
    monkeypatch.setenv("ZHENG_SECRET", "test-secret-key")
    secret = "test-secret-key"
    prefixes = ["STEAM", "ZHENG", "原味", "锁鲜", "蛇口"]
    today = datetime.date.today().isoformat()
    good = codes.generate_member_code(today, secret, prefixes)
    book = codes.generate_booking_code(
        (datetime.date.today() + datetime.timedelta(days=3)).isoformat(), secret)
    book_path = tmp_path / "登记本.txt"
    book_path.write_text(
        f"午市 张三 {good}\n晚市 李四 {book}\n王五报了把假码 原味-20990101-0000-AAAAAA\n",
        encoding="utf-8")
    result = CliRunner().invoke(cli, ["verify", "--file", str(book_path)])
    assert "共识别 3 把" in result.output
    assert "有效 2 · 无效 1" in result.output
