import json
from pathlib import Path
from datetime import datetime
from html import escape

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def load_json(agent_name):
    date = today_str()
    path = REPORT_DIR / f"{date}_{agent_name}.json"

    if not path.exists():
        return None, path

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


def json_to_pretty_text(data):
    return escape(json.dumps(data, ensure_ascii=False, indent=2))


def build_summary_text(market, sector, stock):
    market_status = market.get("market_breadth", {}).get("market_sentiment", "暂无")
    sector_text = sector.get("analysis") or sector.get("summary") or "暂无板块分析结果"
    stock_text = stock.get("summary") or stock.get("analysis") or "暂无个股分析结果"

    return f"""
    <p><strong>综合判断：</strong>今日市场情绪为 <strong>{escape(str(market_status))}</strong>。</p>
    <p><strong>板块观察：</strong>{escape(str(sector_text))}</p>
    <p><strong>个股观察：</strong>{escape(str(stock_text))}</p>
    <p><strong>操作建议：</strong>建议结合大盘情绪、热点板块强度与个股技术指标进行综合判断，避免单一指标决策。</p>
    """


def generate_html(market, sector, stock):
    date = today_str()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>每日股票分析汇总报告</title>
    <style>
        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
            background: #f4f6f9;
            color: #222;
        }}
        header {{
            background: linear-gradient(135deg, #1f4e79, #2f75b5);
            color: white;
            padding: 36px 48px;
        }}
        header h1 {{
            margin: 0;
            font-size: 32px;
        }}
        header p {{
            margin-top: 10px;
            font-size: 16px;
        }}
        main {{
            padding: 32px 48px;
        }}
        .card {{
            background: white;
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        }}
        .card h2 {{
            margin-top: 0;
            color: #1f4e79;
            border-left: 5px solid #2f75b5;
            padding-left: 12px;
        }}
        pre {{
            background: #f7f9fb;
            padding: 16px;
            border-radius: 10px;
            overflow-x: auto;
            line-height: 1.5;
        }}
        .tag {{
            display: inline-block;
            padding: 6px 12px;
            background: #e8f1fb;
            color: #1f4e79;
            border-radius: 999px;
            margin-right: 8px;
            font-size: 14px;
        }}
        footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
<header>
    <h1>每日股票分析数字员工系统</h1>
    <p>生成日期：{date}</p>
    <span class="tag">大盘分析</span>
    <span class="tag">板块分析</span>
    <span class="tag">个股分析</span>
    <span class="tag">组长汇总</span>
</header>

<main>
    <section class="card">
        <h2>一、综合分析结论</h2>
        {build_summary_text(market, sector, stock)}
    </section>

    <section class="card">
        <h2>二、A 大盘分析机器人结果</h2>
        <pre>{json_to_pretty_text(market)}</pre>
    </section>

    <section class="card">
        <h2>三、B 板块分析机器人结果</h2>
        <pre>{json_to_pretty_text(sector)}</pre>
    </section>

    <section class="card">
        <h2>四、C 个股分析机器人结果</h2>
        <pre>{json_to_pretty_text(stock)}</pre>
    </section>
</main>

<footer>
    OpenClaw + 飞书机器人 + AkShare + HTML 汇总展示
</footer>
</body>
</html>
"""
    return html


def main():
    market, market_path = load_json("market")
    sector, sector_path = load_json("sector")
    stock, stock_path = load_json("stock")

    missing = []
    if market is None:
        missing.append(str(market_path))
    if sector is None:
        missing.append(str(sector_path))
    if stock is None:
        missing.append(str(stock_path))

    if missing:
        print("缺少以下报告文件，请先运行对应 Agent：")
        for item in missing:
            print("-", item)
        return

    date = today_str()
    output_path = REPORT_DIR / f"{date}_final_report.html"

    html = generate_html(market, sector, stock)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"汇总 HTML 已生成：{output_path}")


if __name__ == "__main__":
    main()
