import json
import random
from common import today_str, save_report


def build_report():
    sectors = ["人工智能", "半导体", "新能源", "医药", "消费", "机器人", "算力"]
    selected = random.sample(sectors, 3)
    ranking = []
    for s in selected:
        ranking.append({
            "板块": s,
            "涨跌幅": f"{round(random.uniform(-1.5, 4.5), 2)}%",
            "资金状态": random.choice(["主力流入", "小幅流入", "分歧加大", "资金流出"]),
            "热度": random.choice(["高", "中", "低"])
        })
    report = {
        "agent": "sector",
        "date": today_str(),
        "module": "板块分析",
        "data_source": "演示数据；最终提交前建议替换为真实板块行情 API",
        "hot_sectors": ranking,
        "summary": f"今日重点关注 {selected[0]}、{selected[1]}、{selected[2]}，板块间轮动明显。",
        "risk": "热点板块涨幅过大时容易出现追高风险，应观察资金持续性。",
        "suggestion": "优先关注资金连续流入、涨幅不过热、与政策或业绩逻辑匹配的板块。"
    }
    return report


if __name__ == "__main__":
    result = build_report()
    save_report("sector", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
