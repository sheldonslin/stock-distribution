#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票涨跌分布 — 腾讯财经接口版
零依赖，纯标准库，GitHub Actions 海外IP可用
数据源：qt.gtimg.cn（腾讯不封海外IP）
"""

import json
import os
import sys
import urllib.request
import concurrent.futures
from datetime import datetime, timezone, timedelta

OUTPUT_DIR = "dist"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "data.json")
BJ_TZ = timezone(timedelta(hours=8))
BATCH_SIZE = 80
CONCURRENCY = 10
TIMEOUT = 15

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# A股全部代码（沪深主板+创业板+科创板+北交所）
STOCK_CODES_FILE = os.path.join(os.path.dirname(__file__), "stock_codes.json")


def now_bj():
    return datetime.now(BJ_TZ)


def log(msg):
    print(f"[{now_bj().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def generate_stock_codes():
    """生成全部A股代码列表"""
    codes = []
    # 沪市主板 600000-605999
    for i in range(600000, 606000):
        codes.append(f"sh{i}")
    # 沪市科创板 688000-689999
    for i in range(688000, 690000):
        codes.append(f"sh{i}")
    # 深市主板 000001-003999
    for i in range(1, 4000):
        codes.append(f"sz{i:06d}")
    # 深市中小板（已合并到主板）002001-002999
    # 已包含在上面
    # 深市创业板 300001-301999
    for i in range(300001, 302000):
        codes.append(f"sz{i}")
    # 北交所 8xxxxx -> bj
    for i in range(430001, 430999):
        codes.append(f"bj{i}")
    for i in range(830001, 840000):
        codes.append(f"bj{i}")
    for i in range(870001, 880000):
        codes.append(f"bj{i}")
    return codes


def load_stock_codes():
    """优先从文件加载，没有就自动生成"""
    if os.path.exists(STOCK_CODES_FILE):
        with open(STOCK_CODES_FILE, "r") as f:
            codes = json.load(f)
        log(f"从文件加载 {len(codes)} 个代码")
        return codes
    codes = generate_stock_codes()
    log(f"自动生成 {len(codes)} 个代码")
    return codes


def fetch_batch(batch):
    """请求一批股票数据"""
    url = f"https://qt.gtimg.cn/q={','.join(batch)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("gbk", errors="ignore")
    except Exception:
        return []

    results = []
    for line in raw.split(";"):
        line = line.strip()
        if not line or "~" not in line:
            continue
        parts = line.split("~")
        if len(parts) < 40:
            continue
        try:
            pct = float(parts[32])
        except (ValueError, IndexError):
            continue
        results.append({"code": parts[2], "name": parts[1], "pct": pct})
    return results


def fetch_all_stocks():
    """并发获取全部股票数据"""
    codes = load_stock_codes()
    batches = [codes[i:i + BATCH_SIZE] for i in range(0, len(codes), BATCH_SIZE)]
    log(f"共 {len(codes)} 个代码，分 {len(batches)} 批，并发 {CONCURRENCY}")

    all_stocks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(fetch_batch, b): i for i, b in enumerate(batches)}
        for future in concurrent.futures.as_completed(futures):
            all_stocks.extend(future.result())

    log(f"获取到 {len(all_stocks)} 只有效数据")
    return all_stocks


def calc_distribution(stocks):
    dist = {"涨停": 0, "涨5-10%": 0, "涨0-5%": 0, "平盘": 0, "跌0-5%": 0, "跌5-10%": 0, "跌停": 0}
    up = down = flat = 0
    for s in stocks:
        p = s["pct"]
        if p > 9.8:
            dist["涨停"] += 1; up += 1
        elif p > 5:
            dist["涨5-10%"] += 1; up += 1
        elif p > 0.01:
            dist["涨0-5%"] += 1; up += 1
        elif p >= -0.01:
            dist["平盘"] += 1; flat += 1
        elif p >= -5:
            dist["跌0-5%"] += 1; down += 1
        elif p >= -9.8:
            dist["跌5-10%"] += 1; down += 1
        else:
            dist["跌停"] += 1; down += 1
    return {
        "distribution": dist,
        "summary": {"up_count": up, "down_count": down, "flat_count": flat, "total_count": len(stocks)}
    }


def main():
    try:
        stocks = fetch_all_stocks()
        if len(stocks) < 100:
            raise RuntimeError(f"数据不足: {len(stocks)}")

        result = calc_distribution(stocks)
        output = {
            "status": "success",
            "data": result,
            "last_updated": now_bj().strftime("%Y-%m-%d %H:%M:%S"),
        }

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        s = result["summary"]
        log(f"完成！总计 {s['total_count']} | 涨 {s['up_count']} | 跌 {s['down_count']} | 平 {s['flat_count']}")
        log(f"分布: {result['distribution']}")
        log(f"输出: {OUTPUT_FILE}")

    except Exception as e:
        log(f"失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
