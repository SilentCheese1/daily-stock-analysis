import json
import random
from common import today_str, save_report


def build_report():
    # 第一版使用演示数据，保证小白先跑通流程；最终版建议替换为 AkShare/Tushare/东方财富真实数据。
    sh = round(3000 + random.uniform(-30, 30), 2)
    sz = round(9500 + random.uniform(-120, 120), 2)
    cyb = round(1800 + random.uniform(-40, 40), 2)
    up_count = random.randint(1800, 3600)
    down_count = random.randint(1200, 3200)
    sentiment = "偏强" if up_count > down_count else "偏弱"
    report = {
        "agent": "market",
        "date": today_str(),
        "module": "大盘分析",
        "data_source": "演示数据；最终提交前建议替换为真实行情 API",
        "index_analysis": {
            "上证指数": sh,
            "深证成指": sz,
            "创业板指": cyb,
            "上涨家数": up_count,
            "下跌家数": down_count,
            "市场情绪": sentiment
        },
        "summary": f"今日大盘整体表现{sentiment}，上涨家数 {up_count}，下跌家数 {down_count}。",
        "risk": "注意指数冲高回落、成交量不足和热点快速轮动风险。",
        "suggestion": "控制仓位，优先关注低位放量、基本面清晰的方向。"
    }
    return report


if __name__ == "__main__":
    result = build_report()
    save_report("market", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
