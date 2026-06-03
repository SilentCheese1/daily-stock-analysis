import json
import random
from common import today_str, save_report

WATCH_STOCKS = ["宁德时代", "中际旭创", "比亚迪"]


def build_report():
    stocks = []
    for name in WATCH_STOCKS:
        stocks.append({
            "股票名称": name,
            "趋势": random.choice(["震荡上行", "横盘整理", "短线回调", "放量突破"]),
            "MA": random.choice(["MA5 位于 MA10 上方", "MA5 接近 MA10", "短期均线走平"]),
            "MACD": random.choice(["红柱放大", "绿柱缩短", "零轴附近震荡"]),
            "RSI": random.randint(35, 75),
            "建议": random.choice(["观察为主", "不追高，等待回踩", "小仓位关注", "风险偏高，谨慎"])
        })
    report = {
        "agent": "stock",
        "date": today_str(),
        "module": "个股分析",
        "data_source": "演示数据；最终提交前建议替换为真实个股行情 API",
        "stocks": stocks,
        "summary": "重点个股分化较明显，应结合板块热度、均线和成交量判断。",
        "risk": "单只股票波动大，不能只根据 AI 文本做买卖决策。",
        "suggestion": "选择趋势稳定、成交量配合、所在板块有热度的个股进行跟踪。"
    }
    return report


if __name__ == "__main__":
    result = build_report()
    save_report("stock", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
