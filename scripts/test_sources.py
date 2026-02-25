#!/usr/bin/env python3
"""测试各数据源能否从GitHub Actions（海外IP）访问"""
import urllib.request
import json

# 东财push2接口 - 获取A股所有个股行情（akshare底层就是调这个）
# 这个URL是精简版，只取5条测试连通性
EASTMONEY_PUSH2 = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f2,f3,f12,f14"

# 东财行情中心 - 另一个域名的行情接口
EASTMONEY_QUOTE = "https://quote.eastmoney.com/center/gridlist.html"

# 东财push2ex - 备用push接口
EASTMONEY_PUSH2EX = "https://push2ex.eastmoney.com/getStockFenShi?pagesize=1&ut=7eea3edcaed734bea9cb&dpt=wzfscj&cb=&pageindex=0&id=0000011&sort=1&ft=1"

# 腾讯行情接口 - 获取个股行情
TENCENT_QT = "https://qt.gtimg.cn/q=sh600519,sh601318,sz000001"

# 腾讯行情 - 批量获取（web.ifzq.gtimg.cn）
TENCENT_IFZQ = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600519,day,,,5,qfq"

sources = {
    "东财push2(akshare底层)": EASTMONEY_PUSH2,
    "东财push2ex": EASTMONEY_PUSH2EX,
    "腾讯qt.gtimg.cn": TENCENT_QT,
    "腾讯web.ifzq": TENCENT_IFZQ,
}

for name, url in sources.items():
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        req.add_header("Referer", "https://quote.eastmoney.com/")
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(800)
            data = raw.decode('utf-8', errors='ignore')
            print(f"✅ {name}")
            print(f"   Status: {resp.status}")
            print(f"   Data: {data[:300]}")
    except Exception as e:
        print(f"❌ {name}: {e}")
    print()
