#!/usr/bin/env python3
"""测试腾讯行情接口批量获取能力 + 其他获取A股代码列表的方式"""
import urllib.request
import json
import time

# 方案A：用东财的 web 版接口获取代码列表（不是push2，是另一个域名）
print("=== 测试东财web版接口获取代码列表 ===")
try:
    # 东财行情中心的API，全量获取代码和涨跌幅
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f2,f3,f12,f13,f14"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = data.get("data", {}).get("total", 0)
        print(f"  总数: {total}")
        diff = data.get("data", {}).get("diff", {})
        for k in list(diff.keys())[:5]:
            item = diff[k]
            print(f"  {item.get('f12')} {item.get('f14')} 涨跌幅:{item.get('f3')}%")
except Exception as e:
    print(f"  失败: {e}")

print()

# 方案B：直接用东财push2一次性获取全部个股涨跌幅（pz=6000）
print("=== 测试东财push2一次获取全部(pz=6000) ===")
try:
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=6000&po=1&np=1&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f3"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    req.add_header("Referer", "https://quote.eastmoney.com/center/gridlist.html")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        data = json.loads(raw)
        total = data.get("data", {}).get("total", 0)
        diff = data.get("data", {}).get("diff", [])
        if isinstance(diff, dict):
            diff = list(diff.values())
        print(f"  总数: {total}, 返回: {len(diff)}")
except Exception as e:
    print(f"  失败: {e}")

print()

# 方案C：腾讯行情批量 - 测试一次能请求多少个
print("=== 测试腾讯行情批量请求容量 ===")
# 生成100个测试代码
codes = [f"sh60{i:04d}" for i in range(100)]
url = "https://qt.gtimg.cn/q=" + ",".join(codes)
try:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("gbk", errors="ignore")
        valid = [l for l in raw.strip().split(";") if "~" in l and len(l) > 20]
        print(f"  请求100个代码，返回有效: {len(valid)} 条")
except Exception as e:
    print(f"  失败: {e}")

print()

# 方案D：用一个公开的A股代码列表API
print("=== 测试获取A股代码列表(沪深交易所) ===")
try:
    # 沪市
    url_sh = "https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1110x&TABKEY=tab1&random=0.1"
    req = urllib.request.Request(url_sh)
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"  深交所API: status={resp.status}")
except Exception as e:
    print(f"  深交所API失败: {e}")

print("\n=== 总结 ===")
print("如果东财push2在海外被封，最佳方案是：")
print("1. 在仓库中维护一个A股代码列表文件（每月更新一次）")
print("2. 用腾讯qt.gtimg.cn批量获取涨跌幅（海外不封）")
print("3. 这样完全不依赖akshare，也不需要pandas/numpy等重依赖")
