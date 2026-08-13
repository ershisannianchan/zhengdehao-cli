#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用途：日期/人数解析的边界测试。"""
import datetime

from zheng import parse_date, parse_persons


def test_parse_date_formats():
    year = datetime.date.today().year
    assert parse_date("8.1") == f"{year}-08-01"
    assert parse_date("8/1") == f"{year}-08-01"
    assert parse_date("801") == f"{year}-08-01"
    assert parse_date("2026-08-01") == "2026-08-01"


def test_parse_date_invalid():
    assert parse_date("13/1") is None     # 13 月不存在
    assert parse_date("2/30") is None     # 2 月 30 日不存在
    assert parse_date("") is None
    assert parse_date(None) is None


def test_parse_persons():
    assert parse_persons("8") == 8
    assert parse_persons("8人") == 8
    assert parse_persons("8 人") == 8
    assert parse_persons("8位") == 8
    assert parse_persons(None) is None
    assert parse_persons("abc") is None
