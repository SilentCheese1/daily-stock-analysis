import json
from pathlib import Path
from common import today_str, load_report, REPORT_DIR


def ensure_reports():
    # 如果没有三份 JSON，提示先运行三个 Agent。
    missing = []
    data = {}
    for name in ["market", "sector", "stock"]:
        item = load_report(name)
        if item is None:
            missing.append(name)
        else:
            data[name] = item
    return data, missing


def build_markdown(data: dict):
    market = data.get("market", {})
    sector = data.get("sector", {})
    stock = data.get("stock", {})
    date = today_str()
    lines = [
        f"# 每日股票分析综合日报（{date}）",
        "",
        "## 1. 大盘总结",
        market.get("summary", "暂无大盘分析结果"),
        "",
        "## 2. 热门板块",
        sector.get("summary", "暂无板块分析结果"),
        "",
        "## 3. 重点个股",
        stock.get("summary", "暂无个股分析结果"),
        "",
        "## 4. 风险提示",
        f"- 大盘风险：{market.get('risk', '暂无')}",
        f"- 板块风险：{sector.get('risk', '暂无')}",
        f"- 个股风险：{stock.get('risk', '暂无')}",
        "",
        "## 5. 每日操作建议",
        f"- {market.get('suggestion', '暂无')}",
        f"- {sector.get('suggestion', '暂无')}",
        f"- {stock.get('suggestion', '暂无')}",
        "",
        "> 说明：本报告用于课程作业演示，不构成真实投资建议。最终提交前请替换为真实数据源。"
    ]
    return "\n".join(lines)


def save_html(markdown_text: str):
    html_body = markdown_text.replace("\n", "<br>")
    html = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>每日股票分析综合日报</title>
<style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:900px;margin:40px auto;line-height:1.8;color:#1f2937}}h1{{color:#0f172a}}h2{{border-left:5px solid #2563eb;padding-left:10px}}code,pre{{background:#f3f4f6;padding:8px;border-radius:8px}}</style></head><body>{html_body}</body></html>"""
    path = REPORT_DIR / f"{today_str()}_final_report.html"
    path.write_text(html, encoding="utf-8")
    return path


if __name__ == "__main__":
    data, missing = ensure_reports()
    if missing:
        print(json.dumps({
            "ok": False,
            "message": "请先运行缺失的 Agent",
            "missing": missing,
            "example": "python agents/market_agent.py && python agents/sector_agent.py && python agents/stock_agent.py"
        }, ensure_ascii=False, indent=2))
    else:
        md = build_markdown(data)
        path = save_html(md)
        print(md)
        print(f"\n已保存 HTML 报告：{path}")
