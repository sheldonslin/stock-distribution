#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===========================================
股票涨跌分布数据抓取脚本
===========================================
用途：通过 akshare 抓取A股实时涨跌分布，生成 JSON 文件
参数：无
输出：dist/data.json
说明：
  - 由 GitHub Actions 定时调用
  - 交易日 9:30-15:00 每20分钟跑一次
  - 非交易时间由 Actions 的 cron 控制，脚本本身不做时间判断
  - 内置重试机制（5次）+ 浏览器请求头伪装，绕过东财反爬
  - 时间戳使用北京时间（UTC+8）
===========================================
"""

import akshare as ak
import requests
import pandas as pd
import json
import os
import sys
import time
import random
from datetime import datetime, timezone, timedelta

# ============================================
# 配置区
# ============================================
OUTPUT_DIR = "dist"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "data.json")
MAX_RETRIES = 5
RETRY_DELAY = 15  # 秒

# 北京时间
BJ_TZ = timezone(timedelta(hours=8))

# 浏览器 User-Agent 池，随机选一个伪装请求
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

# 涨跌幅区间定义
RANGES = {
    '涨停': (9.8, float('inf')),
    '上涨5-10%': (5, 9.8),
    '上涨0-5%': (0.01, 5),
    '平盘': (0, 0),
    '下跌0-5%': (-5, -0.01),
    '下跌5-10%': (-9.8, -5),
    '跌停': (float('-inf'), -9.8)
}


def now_bj():
    """返回北京时间"""
    return datetime.now(BJ_TZ)


def patch_requests_headers():
    """给 requests 全局 Session 打补丁，伪装浏览器请求头，绕过东财反爬"""
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
    }
    # 猴子补丁：替换 requests.Session 的默认 headers
    original_init = requests.Session.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.headers.update(headers)

    requests.Session.__init__ = patched_init

    # 也给 requests.get/post 的默认 headers 打补丁
    if hasattr(requests, 'utils'):
        requests.utils.default_headers = lambda: requests.structures.CaseInsensitiveDict(headers)

    print(f"[{now_bj().strftime('%Y-%m-%d %H:%M:%S')}] 已伪装浏览器请求头: {ua[:50]}...")


def fetch_with_retry():
    """带重试的数据抓取，每次重试前重新伪装请求头"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                jitter = random.uniform(3, 8)
                print(f"  随机等待{jitter:.1f}秒...")
                time.sleep(jitter)
            patch_requests_headers()
            print(f"[{now_bj().strftime('%Y-%m-%d %H:%M:%S')}] 第{attempt}次尝试获取数据...")
            df = ak.stock_zh_a_spot_em()
            print(f"[{now_bj().strftime('%Y-%m-%d %H:%M:%S')}] 数据获取成功，共{len(df)}条")
            return df
        except Exception as e:
            print(f"[{now_bj().strftime('%Y-%m-%d %H:%M:%S')}] 第{attempt}次失败: {e}")
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY * attempt
                print(f"  等待{delay}秒后重试...")
                time.sleep(delay)
            else:
                raise


def fetch_market_distribution():
    """抓取A股涨跌分布数据"""
    print(f"[{now_bj().strftime('%Y-%m-%d %H:%M:%S')}] 开始获取市场涨跌分布数据...")

    df = fetch_with_retry()
    df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
    df = df.dropna(subset=['涨跌幅'])

    distribution = {}
    for name, (lower, upper) in RANGES.items():
        if lower == upper:
            count = int(df[df['涨跌幅'] == lower].shape[0])
        else:
            count = int(df[(df['涨跌幅'] > lower) & (df['涨跌幅'] <= upper)].shape[0])
        distribution[name] = count

    up_count = int(df[df['涨跌幅'] > 0].shape[0])
    down_count = int(df[df['涨跌幅'] < 0].shape[0])

    data = {
        "status": "success",
        "data": {
            "distribution": distribution,
            "summary": {
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": distribution.get('平盘', 0),
                "total_count": len(df)
            }
        },
        "last_updated": now_bj().strftime('%Y-%m-%d %H:%M:%S')
    }

    return data


def main():
    try:
        patch_requests_headers()
        data = fetch_market_distribution()

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        summary = data['data']['summary']
        print(f"[{now_bj().strftime('%Y-%m-%d %H:%M:%S')}] 数据更新完成！")
        print(f"  总计: {summary['total_count']} | 涨: {summary['up_count']} | 跌: {summary['down_count']} | 平: {summary['flat_count']}")
        print(f"  输出: {OUTPUT_FILE}")

    except Exception as e:
        print(f"[{now_bj().strftime('%Y-%m-%d %H:%M:%S')}] 抓取数据失败（已重试{MAX_RETRIES}次）: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
