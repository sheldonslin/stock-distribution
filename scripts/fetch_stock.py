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
===========================================
"""

import akshare as ak
import pandas as pd
import json
import os
import sys
from datetime import datetime

# ============================================
# 配置区
# ============================================
OUTPUT_DIR = "dist"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "data.json")

# 涨跌幅区间定义（和你原来的逻辑一致）
RANGES = {
    '涨停': (9.8, float('inf')),
    '上涨5-10%': (5, 9.8),
    '上涨0-5%': (0.01, 5),
    '平盘': (0, 0),
    '下跌0-5%': (-5, -0.01),
    '下跌5-10%': (-9.8, -5),
    '跌停': (float('-inf'), -9.8)
}


def fetch_market_distribution():
    """抓取A股涨跌分布数据"""
    print(f"[{datetime.now()}] 开始获取市场涨跌分布数据...")

    df = ak.stock_zh_a_spot_em()
    df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
    df = df.dropna(subset=['涨跌幅'])

    # 计算各区间数量
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
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    return data


def main():
    try:
        data = fetch_market_distribution()

        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 写入 JSON
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        summary = data['data']['summary']
        print(f"[{datetime.now()}] 数据更新完成！")
        print(f"  总计: {summary['total_count']} | 涨: {summary['up_count']} | 跌: {summary['down_count']} | 平: {summary['flat_count']}")
        print(f"  输出: {OUTPUT_FILE}")

    except Exception as e:
        print(f"[{datetime.now()}] 抓取数据失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
