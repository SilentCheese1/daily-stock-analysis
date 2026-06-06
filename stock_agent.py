import os
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
# agents/stock_agent.py
import requests
import pandas as pd
import json
import os
from datetime import datetime

# 股票代码列表
# sh开头 = 上证，sz开头 = 深证
stock_codes = ["sz300750", "sz002156", "sz002594"]  # 宁德时代、中际旭创、比亚迪
url = f"http://hq.sinajs.cn/list={','.join(stock_codes)}"

try:
    resp = requests.get(url, timeout=5)
    resp.encoding = 'gbk'  # 新浪返回GBK编码
    data = resp.text.strip().split("\n")
except Exception as e:
    print("网络请求失败，使用假数据:", e)
    data = []

# 解析数据
stocks_list = []
for line in data:
    # 示例返回：
    # var hq_str_sz300750="宁德时代,513.0,520.0,515.5,520.5,...";
    try:
        name = line.split('"')[1].split(',')[0]
        price = float(line.split('"')[1].split(',')[3])  # 当前价格
        change = float(line.split('"')[1].split(',')[4]) - price  # 涨跌
        stocks_list.append({
            "name": name,
            "price": price,
            "change": change,
            "suggestion": "根据趋势和成交量判断操作"
        })
    except:
        continue

# 如果解析失败就用假数据
if not stocks_list:
    stocks_list = [
        {"name": "宁德时代", "price": 513, "change": 7, "suggestion": "观察趋势"},
        {"name": "中际旭创", "price": 28, "change": 0.5, "suggestion": "观察趋势"},
        {"name": "比亚迪", "price": 250, "change": -2, "suggestion": "观察趋势"}
    ]

# 构造JSON
result = {
    "agent": "stock",
    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "stocks": stocks_list,
    "risk": "个股受消息和板块轮动影响较大。",
    "suggestion": "选择趋势稳定、成交量配合的个股，避免重仓单一股票。"
}

# 写入data文件夹
os.makedirs("data", exist_ok=True)
with open("data/stock.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(json.dumps(result, ensure_ascii=False, indent=2))