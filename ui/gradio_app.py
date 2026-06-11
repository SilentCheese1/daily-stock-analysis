import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
from fastapi import FastAPI, Header, HTTPException, Request
import uvicorn


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_TOKEN = os.getenv("REPORT_UPLOAD_TOKEN", "stock-demo-token")
UI_USER = os.getenv("STOCK_UI_USER", "admin")
UI_PASSWORD = os.getenv("STOCK_UI_PASSWORD", "20250607")


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def to_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value)
    text = text.replace(",", "")
    text = text.replace("%", "")
    text = text.replace("亿元", "")
    text = text.replace("亿", "")
    text = text.replace("万元", "")
    text = text.replace("万", "")
    text = text.strip()

    match = re.search(r"-?\d+\.?\d*", text)
    if not match:
        return default

    try:
        return float(match.group())
    except Exception:
        return default


def latest_available_date():
    dates = set()

    for path in REPORT_DIR.glob("*.json"):
        match = re.match(r"(\d{4}-\d{2}-\d{2})_(market|sector|stock)\.json", path.name)
        if match:
            dates.add(match.group(1))

    if today_str() in dates:
        return today_str()

    if dates:
        return sorted(dates)[-1]

    return today_str()


def report_path(agent_name, report_date=None):
    report_date = report_date or latest_available_date()
    return REPORT_DIR / f"{report_date}_{agent_name}.json"


def load_json(agent_name, report_date=None):
    path = report_path(agent_name, report_date)

    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_uploaded_report(agent_name, report_date, data):
    output_path = REPORT_DIR / f"{report_date}_{agent_name}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return output_path


def get_market_rows(market):
    rows = []

    if not market:
        return pd.DataFrame(columns=["指数名称", "最新点位", "涨跌幅(%)", "成交量", "状态"])

    index_analysis = market.get("index_analysis") or market.get("indices") or {}

    if isinstance(index_analysis, dict):
        for name, item in index_analysis.items():
            if not isinstance(item, dict):
                continue

            latest = item.get("latest") or item.get("最新点位") or item.get("close") or item.get("收盘")
            change_pct = item.get("change_pct") or item.get("涨跌幅") or item.get("涨跌幅%") or item.get("pct_chg")
            volume = item.get("volume") or item.get("成交量") or item.get("vol") or item.get("amount") or "暂无"
            status = item.get("status") or item.get("状态") or "已获取"

            rows.append(
                {
                    "指数名称": str(name),
                    "最新点位": latest if latest is not None else "暂无",
                    "涨跌幅(%)": change_pct if change_pct is not None else "暂无",
                    "成交量": volume,
                    "状态": status,
                }
            )

    return pd.DataFrame(rows, columns=["指数名称", "最新点位", "涨跌幅(%)", "成交量", "状态"])


def get_breadth_rows(market):
    if not market:
        return pd.DataFrame(columns=["指标", "数值"])

    breadth = market.get("market_breadth") or market.get("breadth") or {}

    rows = [
        {"指标": "上涨家数", "数值": breadth.get("up_count", "暂无")},
        {"指标": "下跌家数", "数值": breadth.get("down_count", "暂无")},
        {"指标": "平盘家数", "数值": breadth.get("flat_count", "暂无")},
        {"指标": "平均涨跌幅", "数值": breadth.get("avg_change_pct", "暂无")},
        {"指标": "市场情绪", "数值": breadth.get("market_sentiment", "暂无")},
    ]

    return pd.DataFrame(rows)


def get_sector_rows(sector):
    rows = []

    if not sector:
        return pd.DataFrame(columns=["排名", "板块名称", "涨跌幅(%)", "主力资金流向", "热度说明"])

    candidates = [
        sector.get("top_sectors"),
        sector.get("hot_sectors"),
        sector.get("sector_list"),
        sector.get("sectors"),
        sector.get("results"),
        sector.get("data"),
    ]

    sector_list = None
    for item in candidates:
        if isinstance(item, list) and len(item) > 0:
            sector_list = item
            break

    if sector_list:
        for idx, item in enumerate(sector_list[:15], 1):
            if not isinstance(item, dict):
                rows.append(
                    {
                        "排名": idx,
                        "板块名称": str(item),
                        "涨跌幅(%)": "暂无",
                        "主力资金流向": "暂无",
                        "热度说明": "热点板块",
                    }
                )
                continue

            name = item.get("name") or item.get("板块名称") or item.get("板块") or item.get("sector") or f"板块{idx}"
            change = item.get("change_pct") or item.get("涨跌幅") or item.get("涨跌幅%") or item.get("pct_chg") or "暂无"
            fund = item.get("fund_flow") or item.get("主力资金流向") or item.get("资金流向") or item.get("main_fund") or item.get("net_inflow") or "暂无"
            reason = item.get("reason") or item.get("summary") or item.get("热度说明") or item.get("description") or "热点板块"

            rows.append(
                {
                    "排名": idx,
                    "板块名称": name,
                    "涨跌幅(%)": change,
                    "主力资金流向": fund,
                    "热度说明": reason,
                }
            )

    if not rows:
        summary = sector.get("analysis") or sector.get("summary") or "暂无板块明细，等待板块机器人上传结构化结果。"
        rows.append(
            {
                "排名": 1,
                "板块名称": "综合板块观点",
                "涨跌幅(%)": "暂无",
                "主力资金流向": "暂无",
                "热度说明": summary,
            }
        )

    return pd.DataFrame(rows, columns=["排名", "板块名称", "涨跌幅(%)", "主力资金流向", "热度说明"])


def get_stock_rows(stock):
    rows = []

    columns = [
        "股票名称",
        "代码",
        "最新价",
        "MA5",
        "MA10",
        "MA20",
        "MACD",
        "RSI",
        "KDJ",
        "成交量变化",
        "建议",
    ]

    if not stock:
        return pd.DataFrame(columns=columns)

    stocks = stock.get("stocks") or stock.get("stock_list") or stock.get("results") or stock.get("data")

    if isinstance(stocks, dict):
        stocks = list(stocks.values())

    if isinstance(stocks, list):
        for idx, item in enumerate(stocks[:10], 1):
            if not isinstance(item, dict):
                continue

            rows.append(
                {
                    "股票名称": item.get("name") or item.get("股票名称") or f"股票{idx}",
                    "代码": item.get("code") or item.get("symbol") or item.get("股票代码") or "暂无",
                    "最新价": item.get("price") or item.get("latest") or item.get("最新价") or "暂无",
                    "MA5": item.get("MA5") or item.get("ma5") or "暂无",
                    "MA10": item.get("MA10") or item.get("ma10") or "暂无",
                    "MA20": item.get("MA20") or item.get("ma20") or "暂无",
                    "MACD": item.get("MACD") or item.get("macd") or "暂无",
                    "RSI": item.get("RSI") or item.get("rsi") or "暂无",
                    "KDJ": item.get("KDJ") or item.get("kdj") or "暂无",
                    "成交量变化": item.get("volume_change") or item.get("成交量变化") or item.get("vol_change") or "暂无",
                    "建议": item.get("advice") or item.get("建议") or item.get("signal") or "观察",
                }
            )

    if not rows:
        summary = stock.get("summary") or stock.get("analysis") or "暂无个股明细，等待个股机器人上传结构化结果。"
        rows.append(
            {
                "股票名称": "综合个股观点",
                "代码": "暂无",
                "最新价": "暂无",
                "MA5": "暂无",
                "MA10": "暂无",
                "MA20": "暂无",
                "MACD": "暂无",
                "RSI": "暂无",
                "KDJ": "暂无",
                "成交量变化": "暂无",
                "建议": summary,
            }
        )

    return pd.DataFrame(rows, columns=columns)


def empty_fig(title, message="暂无可视化数据"):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        height=360,
        template="plotly_white",
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16},
            }
        ],
    )
    return fig


def make_market_index_fig(market_df):
    if market_df.empty:
        return empty_fig("大盘指数涨跌幅")

    names = market_df["指数名称"].tolist()
    changes = [to_float(x) for x in market_df["涨跌幅(%)"].tolist()]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=changes, text=changes, textposition="auto"))
    fig.update_layout(
        title="大盘指数涨跌幅对比",
        xaxis_title="指数",
        yaxis_title="涨跌幅(%)",
        height=380,
        template="plotly_white",
    )
    return fig


def make_market_breadth_fig(breadth_df):
    if breadth_df.empty:
        return empty_fig("市场涨跌家数")

    values = {}
    for _, row in breadth_df.iterrows():
        values[str(row["指标"])] = to_float(row["数值"])

    labels = ["上涨家数", "下跌家数", "平盘家数"]
    nums = [values.get("上涨家数", 0), values.get("下跌家数", 0), values.get("平盘家数", 0)]

    if sum(nums) == 0:
        return empty_fig("市场涨跌家数", "暂无涨跌家数数据")

    fig = go.Figure(data=[go.Pie(labels=labels, values=nums, hole=0.35)])
    fig.update_layout(title="市场涨跌家数分布", height=380, template="plotly_white")
    return fig


def make_market_volume_fig(market_df):
    if market_df.empty:
        return empty_fig("大盘成交量")

    names = market_df["指数名称"].tolist()
    volumes = [to_float(x) for x in market_df["成交量"].tolist()]

    if sum(abs(v) for v in volumes) == 0:
        return empty_fig("大盘成交量", "当前大盘结果中暂无成交量字段")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=volumes))
    fig.update_layout(
        title="大盘成交量对比",
        xaxis_title="指数",
        yaxis_title="成交量",
        height=380,
        template="plotly_white",
    )
    return fig


def make_sector_change_fig(sector_df):
    if sector_df.empty:
        return empty_fig("板块涨跌幅排行")

    df = sector_df.copy()
    df["涨跌幅数值"] = df["涨跌幅(%)"].apply(to_float)
    df = df.head(10).sort_values("涨跌幅数值", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["涨跌幅数值"],
            y=df["板块名称"],
            orientation="h",
            text=df["涨跌幅数值"],
            textposition="auto",
        )
    )
    fig.update_layout(
        title="热门板块涨跌幅排行",
        xaxis_title="涨跌幅(%)",
        yaxis_title="板块",
        height=430,
        template="plotly_white",
    )
    return fig


def make_sector_fund_fig(sector_df):
    if sector_df.empty:
        return empty_fig("主力资金流向")

    df = sector_df.copy()
    df["资金数值"] = df["主力资金流向"].apply(to_float)

    if df["资金数值"].abs().sum() == 0:
        return empty_fig("主力资金流向", "当前板块结果中暂无主力资金流向数值")

    df = df.head(10).sort_values("资金数值", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["资金数值"],
            y=df["板块名称"],
            orientation="h",
            text=df["资金数值"],
            textposition="auto",
        )
    )
    fig.update_layout(
        title="热门板块主力资金流向",
        xaxis_title="资金流向",
        yaxis_title="板块",
        height=430,
        template="plotly_white",
    )
    return fig


def extract_stock_history(stock):
    if not stock:
        return []

    history = stock.get("history") or stock.get("kline") or stock.get("price_history")
    if isinstance(history, list) and history:
        return history

    stocks = stock.get("stocks") or stock.get("stock_list") or stock.get("results") or stock.get("data")
    if isinstance(stocks, dict):
        stocks = list(stocks.values())

    if isinstance(stocks, list) and stocks:
        first = stocks[0]
        if isinstance(first, dict):
            history = first.get("history") or first.get("kline") or first.get("price_history")
            if isinstance(history, list):
                return history

    return []


def normalize_history_df(history):
    rows = []

    for item in history:
        if not isinstance(item, dict):
            continue

        rows.append(
            {
                "date": item.get("date") or item.get("日期") or item.get("time") or item.get("时间"),
                "open": to_float(item.get("open") or item.get("开盘")),
                "high": to_float(item.get("high") or item.get("最高")),
                "low": to_float(item.get("low") or item.get("最低")),
                "close": to_float(item.get("close") or item.get("收盘") or item.get("price") or item.get("最新价")),
                "volume": to_float(item.get("volume") or item.get("成交量") or item.get("vol")),
                "ma5": to_float(item.get("MA5") or item.get("ma5")),
                "ma10": to_float(item.get("MA10") or item.get("ma10")),
                "ma20": to_float(item.get("MA20") or item.get("ma20")),
                "macd": to_float(item.get("MACD") or item.get("macd")),
                "rsi": to_float(item.get("RSI") or item.get("rsi")),
                "k": to_float(item.get("K") or item.get("k")),
                "d": to_float(item.get("D") or item.get("d")),
                "j": to_float(item.get("J") or item.get("j")),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["date"])
    return df


def make_kline_fig(stock):
    history = extract_stock_history(stock)
    df = normalize_history_df(history)

    if df.empty:
        return empty_fig("K线图", "当前个股结果中暂无 K 线历史行情字段")

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="K线",
            )
        ]
    )
    fig.update_layout(
        title="个股 K 线图",
        xaxis_title="日期",
        yaxis_title="价格",
        height=430,
        template="plotly_white",
        xaxis_rangeslider_visible=False,
    )
    return fig


def make_ma_fig(stock, stock_df):
    history = extract_stock_history(stock)
    df = normalize_history_df(history)

    if not df.empty and "close" in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["date"], y=df["close"], mode="lines", name="收盘价"))

        for col, label in [("ma5", "MA5"), ("ma10", "MA10"), ("ma20", "MA20")]:
            if col in df.columns and df[col].abs().sum() != 0:
                fig.add_trace(go.Scatter(x=df["date"], y=df[col], mode="lines", name=label))

        fig.update_layout(
            title="MA5 / MA10 / MA20 均线图",
            xaxis_title="日期",
            yaxis_title="价格",
            height=430,
            template="plotly_white",
        )
        return fig

    if stock_df.empty:
        return empty_fig("均线图")

    first = stock_df.iloc[0]
    values = [to_float(first.get("MA5")), to_float(first.get("MA10")), to_float(first.get("MA20"))]

    if sum(abs(v) for v in values) == 0:
        return empty_fig("均线图", "当前个股结果中暂无 MA5/MA10/MA20 数值")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=["MA5", "MA10", "MA20"], y=values, text=values, textposition="auto"))
    fig.update_layout(title="当前个股均线指标", height=380, template="plotly_white")
    return fig


def make_macd_fig(stock, stock_df):
    history = extract_stock_history(stock)
    df = normalize_history_df(history)

    if not df.empty and "macd" in df.columns and df["macd"].abs().sum() != 0:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["date"], y=df["macd"], name="MACD"))
        fig.update_layout(title="MACD 指标图", xaxis_title="日期", yaxis_title="MACD", height=380, template="plotly_white")
        return fig

    if stock_df.empty:
        return empty_fig("MACD 图")

    df2 = stock_df.copy()
    df2["MACD数值"] = df2["MACD"].apply(to_float)

    if df2["MACD数值"].abs().sum() == 0:
        return empty_fig("MACD 图", "当前个股结果中暂无 MACD 数值")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df2["股票名称"], y=df2["MACD数值"], text=df2["MACD数值"], textposition="auto"))
    fig.update_layout(title="个股 MACD 对比", xaxis_title="股票", yaxis_title="MACD", height=380, template="plotly_white")
    return fig


def make_rsi_kdj_fig(stock, stock_df):
    history = extract_stock_history(stock)
    df = normalize_history_df(history)

    if not df.empty:
        fig = go.Figure()
        used = False

        for col, label in [("rsi", "RSI"), ("k", "K"), ("d", "D"), ("j", "J")]:
            if col in df.columns and df[col].abs().sum() != 0:
                fig.add_trace(go.Scatter(x=df["date"], y=df[col], mode="lines", name=label))
                used = True

        if used:
            fig.update_layout(
                title="RSI / KDJ 指标图",
                xaxis_title="日期",
                yaxis_title="指标值",
                height=430,
                template="plotly_white",
            )
            return fig

    if stock_df.empty:
        return empty_fig("RSI / KDJ 图")

    first = stock_df.iloc[0]
    values = [to_float(first.get("RSI")), to_float(first.get("KDJ"))]

    if sum(abs(v) for v in values) == 0:
        return empty_fig("RSI / KDJ 图", "当前个股结果中暂无 RSI/KDJ 数值")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=["RSI", "KDJ"], y=values, text=values, textposition="auto"))
    fig.update_layout(title="当前个股 RSI / KDJ 指标", height=380, template="plotly_white")
    return fig


def make_stock_volume_fig(stock, stock_df):
    history = extract_stock_history(stock)
    df = normalize_history_df(history)

    if not df.empty and "volume" in df.columns and df["volume"].abs().sum() != 0:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="成交量"))
        fig.update_layout(
            title="成交量变化图",
            xaxis_title="日期",
            yaxis_title="成交量",
            height=380,
            template="plotly_white",
        )
        return fig

    if stock_df.empty:
        return empty_fig("成交量变化图")

    df2 = stock_df.copy()
    df2["成交量变化数值"] = df2["成交量变化"].apply(to_float)

    if df2["成交量变化数值"].abs().sum() == 0:
        return empty_fig("成交量变化图", "当前个股结果中暂无成交量变化数值")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df2["股票名称"], y=df2["成交量变化数值"], text=df2["成交量变化数值"], textposition="auto"))
    fig.update_layout(title="个股成交量变化对比", xaxis_title="股票", yaxis_title="成交量变化", height=380, template="plotly_white")
    return fig


def get_summary_text(market, sector, stock):
    market_sentiment = "暂无"
    up_count = "暂无"
    down_count = "暂无"

    if market:
        breadth = market.get("market_breadth") or {}
        market_sentiment = breadth.get("market_sentiment", "暂无")
        up_count = breadth.get("up_count", "暂无")
        down_count = breadth.get("down_count", "暂无")

    sector_summary = "暂无板块分析结果。"
    if sector:
        sector_summary = sector.get("analysis") or sector.get("summary") or "已接收板块分析结果。"

    stock_summary = "暂无个股分析结果。"
    if stock:
        stock_summary = stock.get("analysis") or stock.get("summary") or "已接收个股分析结果。"

    return f"""
## 🤖 AI 生成内容

### 1. 市场总结
今日系统综合大盘指数、涨跌家数、板块热度和个股技术指标进行分析。当前市场情绪为：**{market_sentiment}**。上涨家数为 **{up_count}**，下跌家数为 **{down_count}**。

### 2. 热点板块判断
{sector_summary}

### 3. 个股技术面判断
{stock_summary}

### 4. 风险提示
- 本系统结果来自自动化数据接口和 OpenClaw 智能体分析，可能受到行情接口延迟、字段缺失和网络波动影响。
- 板块和个股短期波动较大，不应只依据单一技术指标进行决策。
- 若市场涨跌家数分化明显，说明市场内部结构可能存在较强差异，需要降低追高风险。

### 5. 每日操作建议
- 若大盘情绪偏强，可重点关注热点板块中趋势较稳定、成交量配合较好的个股。
- 若大盘情绪偏弱，应控制仓位，优先观察 MA5/MA10/MA20 是否形成趋势支撑。
- 若 MACD、RSI、KDJ 指标出现背离或过热，应注意短线回撤风险。
"""


def build_home_cards(market, sector, stock):
    report_date = latest_available_date()

    market_sentiment = "暂无"
    up_count = "暂无"
    down_count = "暂无"

    if market:
        breadth = market.get("market_breadth") or {}
        market_sentiment = breadth.get("market_sentiment", "暂无")
        up_count = breadth.get("up_count", "暂无")
        down_count = breadth.get("down_count", "暂无")

    sector_df = get_sector_rows(sector)
    stock_df = get_stock_rows(stock)

    hot_sector = "暂无"
    if not sector_df.empty:
        hot_sector = str(sector_df.iloc[0]["板块名称"])

    stock_tip = "暂无"
    if not stock_df.empty:
        stock_tip = str(stock_df.iloc[0]["股票名称"])

    html = f"""
<div class="hero">
  <div>
    <div class="hero-title">每日股票分析数字员工系统</div>
    <div class="hero-subtitle">OpenClaw 多智能体协同 · 大盘—板块—个股三级联动 · 自动生成每日简报</div>
  </div>
  <div class="hero-date">数据日期：{report_date}<br>刷新时间：{now_str()}</div>
</div>

<div class="card-grid">
  <div class="metric-card">
    <div class="metric-label">今日大盘情绪</div>
    <div class="metric-value">{market_sentiment}</div>
    <div class="metric-desc">由涨跌家数、指数涨跌幅和市场宽度综合判断</div>
  </div>

  <div class="metric-card">
    <div class="metric-label">上涨 / 下跌家数</div>
    <div class="metric-value">{up_count} / {down_count}</div>
    <div class="metric-desc">用于衡量市场整体赚钱效应</div>
  </div>

  <div class="metric-card">
    <div class="metric-label">热门板块</div>
    <div class="metric-value">{hot_sector}</div>
    <div class="metric-desc">来自板块机器人上传的热点排名</div>
  </div>

  <div class="metric-card">
    <div class="metric-label">推荐关注</div>
    <div class="metric-value">{stock_tip}</div>
    <div class="metric-desc">来自个股机器人技术指标分析</div>
  </div>
</div>

<div class="section-card">
  <h3>系统说明</h3>
  <p>本系统由三个 OpenClaw 数字员工协同完成：大盘分析机器人、板块分析机器人、个股分析机器人。三个机器人运行后将结构化 JSON 结果上传至 Web 接收端，网站自动读取最新结果并生成可视化看板、智能问答和历史日报。</p>
</div>
"""
    return html


def generate_brief_markdown(market, sector, stock):
    market_df = get_market_rows(market)
    sector_df = get_sector_rows(sector)
    stock_df = get_stock_rows(stock)

    lines = []
    lines.append("## 📋 今日综合简报")
    lines.append("")
    lines.append(f"生成时间：{now_str()}")
    lines.append("")
    lines.append("### 一、今日大盘分析")

    if not market_df.empty:
        for _, row in market_df.iterrows():
            lines.append(f"- {row['指数名称']}：最新点位 {row['最新点位']}，涨跌幅 {row['涨跌幅(%)']}%，成交量 {row['成交量']}。")
    else:
        lines.append("- 暂无大盘机器人上传结果。")

    breadth_df = get_breadth_rows(market)
    if not breadth_df.empty:
        breadth_map = dict(zip(breadth_df["指标"], breadth_df["数值"]))
        lines.append(f"- 市场情绪：{breadth_map.get('市场情绪', '暂无')}；上涨家数 {breadth_map.get('上涨家数', '暂无')}，下跌家数 {breadth_map.get('下跌家数', '暂无')}。")

    lines.append("")
    lines.append("### 二、热门板块")

    if not sector_df.empty:
        for _, row in sector_df.head(5).iterrows():
            lines.append(f"- 第 {row['排名']} 名：{row['板块名称']}，涨跌幅 {row['涨跌幅(%)']}，主力资金流向 {row['主力资金流向']}。")
    else:
        lines.append("- 暂无板块机器人上传结果。")

    lines.append("")
    lines.append("### 三、个股技术指标")

    if not stock_df.empty:
        for _, row in stock_df.head(5).iterrows():
            lines.append(
                f"- {row['股票名称']}：MA5/MA10/MA20 为 {row['MA5']}/{row['MA10']}/{row['MA20']}，"
                f"MACD={row['MACD']}，RSI={row['RSI']}，KDJ={row['KDJ']}，建议：{row['建议']}。"
            )
    else:
        lines.append("- 暂无个股机器人上传结果。")

    lines.append("")
    lines.append(get_summary_text(market, sector, stock))

    return "\n".join(lines)


def run_summary_agent():
    script_path = ROOT / "agents" / "summary_agent.py"

    if not script_path.exists():
        return "❌ 找不到 agents/summary_agent.py，无法生成历史 HTML 文件。"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )

    if result.returncode == 0:
        return "✅ 已调用 summary_agent.py 生成综合日报文件。"
    return f"❌ 综合日报生成失败：\n{result.stderr or result.stdout}"


def list_history_reports():
    dates = set()

    for path in REPORT_DIR.glob("*_market.json"):
        dates.add(path.name[:10])
    for path in REPORT_DIR.glob("*_sector.json"):
        dates.add(path.name[:10])
    for path in REPORT_DIR.glob("*_stock.json"):
        dates.add(path.name[:10])
    for path in REPORT_DIR.glob("*_final_report.html"):
        dates.add(path.name[:10])

    if not dates:
        return "## 📜 历史报告\n\n暂无历史报告。"

    lines = ["## 📜 历史报告", ""]

    for date in sorted(dates, reverse=True):
        files = []
        for suffix in ["market.json", "sector.json", "stock.json", "final_report.html"]:
            path = REPORT_DIR / f"{date}_{suffix}"
            if path.exists():
                files.append(path.name)

        lines.append(f"### {date}")
        for file in files:
            lines.append(f"- {file}")
        lines.append("")

    return "\n".join(lines)


def refresh_dashboard():
    report_date = latest_available_date()

    market = load_json("market", report_date)
    sector = load_json("sector", report_date)
    stock = load_json("stock", report_date)

    market_df = get_market_rows(market)
    breadth_df = get_breadth_rows(market)
    sector_df = get_sector_rows(sector)
    stock_df = get_stock_rows(stock)

    status = f"✅ 已刷新最新 OpenClaw 上传结果。当前数据日期：{report_date}"

    return (
        status,
        build_home_cards(market, sector, stock),
        generate_brief_markdown(market, sector, stock),
        market_df,
        breadth_df,
        make_market_index_fig(market_df),
        make_market_breadth_fig(breadth_df),
        make_market_volume_fig(market_df),
        sector_df,
        make_sector_change_fig(sector_df),
        make_sector_fund_fig(sector_df),
        stock_df,
        make_kline_fig(stock),
        make_ma_fig(stock, stock_df),
        make_macd_fig(stock, stock_df),
        make_rsi_kdj_fig(stock, stock_df),
        make_stock_volume_fig(stock, stock_df),
        get_summary_text(market, sector, stock),
        list_history_reports(),
    )


def generate_and_refresh():
    msg = run_summary_agent()
    refreshed = refresh_dashboard()
    status = msg + "\n" + refreshed[0]
    return (status,) + refreshed[1:]


def qa_answer(question):
    question = (question or "").strip()
    report_date = latest_available_date()

    market = load_json("market", report_date)
    sector = load_json("sector", report_date)
    stock = load_json("stock", report_date)

    market_df = get_market_rows(market)
    sector_df = get_sector_rows(sector)
    stock_df = get_stock_rows(stock)

    if not question:
        return "请输入问题，例如：今天适合买什么？AI 板块走势如何？某只股票是否值得关注？"

    answer = []
    answer.append("## 智能问答结果")
    answer.append("")
    answer.append(f"**你的问题：** {question}")
    answer.append("")
    answer.append(f"**数据日期：** {report_date}")
    answer.append("")

    if "买什么" in question or "适合买" in question or "推荐" in question:
        answer.append("### 结论")
        if stock_df.empty:
            answer.append("当前还没有个股机器人上传的结构化结果，因此暂时不能给出具体关注对象。")
        else:
            top = stock_df.iloc[0]
            answer.append(f"当前可优先关注：**{top['股票名称']}**。")
            answer.append("")
            answer.append("### 判断依据")
            answer.append(f"- MA5 / MA10 / MA20：{top['MA5']} / {top['MA10']} / {top['MA20']}")
            answer.append(f"- MACD：{top['MACD']}")
            answer.append(f"- RSI：{top['RSI']}")
            answer.append(f"- KDJ：{top['KDJ']}")
            answer.append(f"- 成交量变化：{top['成交量变化']}")
            answer.append(f"- 系统建议：{top['建议']}")
        answer.append("")
        answer.append("### 风险提示")
        answer.append("该结果仅用于课程项目展示和辅助分析，不构成真实投资建议。")

    elif "板块" in question or "AI" in question or "人工智能" in question:
        answer.append("### 板块分析")
        if sector_df.empty:
            answer.append("当前还没有板块机器人上传结果。")
        else:
            for _, row in sector_df.head(5).iterrows():
                answer.append(f"- {row['板块名称']}：涨跌幅 {row['涨跌幅(%)']}，主力资金流向 {row['主力资金流向']}，说明：{row['热度说明']}")
        answer.append("")
        answer.append("### 解读")
        answer.append("如果某个板块同时具备涨幅靠前、资金流入明显和持续热度，那么它更可能成为短期市场关注方向；如果只有涨幅但资金流入不足，则需要警惕短线回落。")

    elif "大盘" in question or "市场" in question or "情绪" in question:
        answer.append("### 大盘分析")
        if market_df.empty:
            answer.append("当前还没有大盘机器人上传结果。")
        else:
            for _, row in market_df.iterrows():
                answer.append(f"- {row['指数名称']}：最新点位 {row['最新点位']}，涨跌幅 {row['涨跌幅(%)']}%。")
            breadth = get_breadth_rows(market)
            if not breadth.empty:
                breadth_map = dict(zip(breadth["指标"], breadth["数值"]))
                answer.append(f"- 市场情绪：{breadth_map.get('市场情绪', '暂无')}。")
                answer.append(f"- 上涨家数：{breadth_map.get('上涨家数', '暂无')}；下跌家数：{breadth_map.get('下跌家数', '暂无')}。")
        answer.append("")
        answer.append("### 解读")
        answer.append("大盘判断不只看指数涨跌，还要结合上涨家数、下跌家数和成交量。如果指数上涨但下跌家数较多，说明市场分化较强。")

    elif "个股" in question or "股票" in question or "值得关注" in question:
        answer.append("### 个股分析")
        if stock_df.empty:
            answer.append("当前还没有个股机器人上传结果。")
        else:
            for _, row in stock_df.head(5).iterrows():
                answer.append(
                    f"- {row['股票名称']}：MA5/MA10/MA20={row['MA5']}/{row['MA10']}/{row['MA20']}，"
                    f"MACD={row['MACD']}，RSI={row['RSI']}，KDJ={row['KDJ']}，建议：{row['建议']}。"
                )
        answer.append("")
        answer.append("### 解读")
        answer.append("个股是否值得关注，需要同时看趋势、动量和成交量。均线代表趋势，MACD 代表动能，RSI/KDJ 可辅助判断是否过热。")

    else:
        answer.append("### 综合回答")
        answer.append(get_summary_text(market, sector, stock))
        answer.append("")
        answer.append("你也可以继续问：")
        answer.append("- 今天适合买什么？")
        answer.append("- AI 板块走势如何？")
        answer.append("- 今天大盘情绪怎么样？")
        answer.append("- 某只股票是否值得关注？")

    return "\n".join(answer)


custom_css = """
/* ===== Global Dark Theme ===== */
:root {
  --bg-primary: #0b0d17;
  --bg-card: rgba(255,255,255,0.04);
  --bg-card-hover: rgba(255,255,255,0.08);
  --border-color: rgba(255,255,255,0.08);
  --border-accent: rgba(99,102,241,0.3);
  --text-primary: #e0e4f0;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent: #818cf8;
  --accent-glow: #6366f1;
}

.gradio-container {
  background: var(--bg-primary) !important;
  color: var(--text-primary) !important;
  max-width: 1200px !important;
}
body {
  background: var(--bg-primary) !important;
}

/* Headers */
h1, h2, h3, h4, h5, h6, label, .prose {
  color: var(--text-primary) !important;
}

/* Markdown / prose */
.prose p, .prose li, .prose span {
  color: var(--text-secondary) !important;
}

/* Tabs */
.tabs {
  background: transparent !important;
  border: none !important;
}
.tab-nav {
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  margin-bottom: 16px !important;
}
.tab-nav button {
  background: transparent !important;
  color: var(--text-muted) !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 500 !important;
  transition: all 0.2s !important;
}
.tab-nav button:hover {
  background: rgba(99,102,241,0.1) !important;
  color: var(--text-primary) !important;
}
.tab-nav button.selected {
  background: rgba(99,102,241,0.2) !important;
  color: var(--accent) !important;
  box-shadow: 0 0 12px rgba(99,102,241,0.15) !important;
}

/* Buttons */
button.gradio-button, .gr-button {
  border-radius: 12px !important;
  font-weight: 600 !important;
  border: 1px solid var(--border-color) !important;
  transition: all 0.2s !important;
}
button.gradio-button.primary, .gr-button.primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: #fff !important;
  border: none !important;
  box-shadow: 0 4px 16px rgba(99,102,241,0.2) !important;
}
button.gradio-button.primary:hover {
  box-shadow: 0 6px 24px rgba(99,102,241,0.35) !important;
  transform: translateY(-1px);
}

/* Textbox / Input */
.gr-box, .gr-input, textarea, input[type="text"] {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  color: var(--text-primary) !important;
}
.gr-box:focus, textarea:focus, input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(99,102,241,0.15) !important;
}

/* Dataframe / Tables */
table, .gr-table, .dataframe {
  background: transparent !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}
table thead tr, .gr-table thead tr {
  background: rgba(99,102,241,0.1) !important;
}
table th, .gr-table th {
  color: var(--accent) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  padding: 12px 16px !important;
  border: none !important;
  border-bottom: 1px solid var(--border-color) !important;
  text-align: center !important;
}
table td, .gr-table td {
  color: var(--text-primary) !important;
  padding: 10px 16px !important;
  border: none !important;
  border-bottom: 1px solid var(--border-color) !important;
  text-align: center !important;
  font-size: 13px !important;
}
table tr:hover td, .gr-table tr:hover td {
  background: rgba(99,102,241,0.05) !important;
}

/* Plot backgrounds */
.js-plotly-plot, .plot-container {
  border-radius: 16px !important;
  overflow: hidden !important;
}

/* ===== Hero Section ===== */
.hero {
  padding: 28px 32px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.06));
  border: 1px solid var(--border-accent);
  color: var(--text-primary);
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  backdrop-filter: blur(8px);
}
.hero-title {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, #f0f4ff, #a5b4fc, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 6px;
  letter-spacing: -0.3px;
}
.hero-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
}
.hero-date {
  text-align: right;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-muted);
}

/* ===== Card Grid ===== */
.card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.metric-card {
  border-radius: 16px;
  padding: 20px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  transition: all 0.3s;
}
.metric-card:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-accent);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(99,102,241,0.08);
}
.metric-label {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.metric-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.metric-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

/* ===== Section Card ===== */
.section-card {
  border-radius: 16px;
  padding: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  margin-top: 10px;
}
.section-card h3 {
  color: var(--text-primary) !important;
  font-size: 18px !important;
  font-weight: 700 !important;
  margin-bottom: 10px !important;
}
.section-card p {
  color: var(--text-secondary) !important;
  font-size: 14px !important;
  line-height: 1.7 !important;
}

/* ===== Status box ===== */
.gr-box:has(textarea[readonly]) {
  border-color: var(--border-color) !important;
}

/* ===== Tab inner content ===== */
.tabitem {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}

/* ===== Scrollbar ===== */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.2); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.4); }

/* ===== Accent label override for Gradio markdown headers ===== */
.prose strong {
  color: var(--accent) !important;
}
.prose code {
  background: rgba(99,102,241,0.12) !important;
  color: var(--accent) !important;
  border-radius: 6px !important;
  padding: 2px 8px !important;
  font-size: 13px !important;
}
"""

with gr.Blocks(title="每日股票分析数字员工系统", css=custom_css, theme=gr.themes.Default()) as demo:
    gr.HTML("""<div style="margin-bottom:6px">
  <h1 style="font-size:26px;font-weight:800;margin:0;background:linear-gradient(135deg,#f0f4ff,#a5b4fc,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">📊 每日股票分析数字员工系统</h1>
  <p style="color:#94a3b8;font-size:14px;margin:6px 0 0 0;">OpenClaw 多智能体协同分析 · 自动上传结果 · Web 可视化看板</p>
</div>")


with gr.Blocks(title="每日股票分析数字员工系统", css=custom_css) as demo:
    gr.HTML("<h1>📊 每日股票分析数字员工系统</h1><p>OpenClaw 多智能体协同分析 · 自动上传结果 · Web 可视化看板</p>")

    with gr.Row():
        refresh_btn = gr.Button("🔄 刷新 OpenClaw 上传结果", variant="primary")
        summary_btn = gr.Button("🧾 生成/更新每日简报")
        history_btn = gr.Button("📜 刷新历史报告")

    status_box = gr.Textbox(label="系统状态", value="等待刷新。", interactive=False)

    with gr.Tabs():
        with gr.Tab("🏠 每日分析首页"):
            home_html = gr.HTML()

        with gr.Tab("📋 今日综合简报"):
            brief_md = gr.Markdown()

        with gr.Tab("📈 大盘分析"):
            gr.Markdown("### 大盘指标")
            market_table = gr.Dataframe(interactive=False)
            gr.Markdown("### 涨跌家数")
            breadth_table = gr.Dataframe(interactive=False)
            with gr.Row():
                market_index_plot = gr.Plot()
                market_breadth_plot = gr.Plot()
            market_volume_plot = gr.Plot()

        with gr.Tab("🏭 板块分析"):
            gr.Markdown("### 板块涨跌幅、主力资金流向与热点排名")
            sector_table = gr.Dataframe(interactive=False)
            with gr.Row():
                sector_change_plot = gr.Plot()
                sector_fund_plot = gr.Plot()

        with gr.Tab("💎 个股分析"):
            gr.Markdown("### 个股技术指标")
            stock_table = gr.Dataframe(interactive=False)
            gr.Markdown("### 图表展示")
            kline_plot = gr.Plot()
            ma_plot = gr.Plot()
            macd_plot = gr.Plot()
            rsi_kdj_plot = gr.Plot()
            stock_volume_plot = gr.Plot()

        with gr.Tab("🤖 智能问答"):
            gr.Markdown(
                """
你可以询问：
- 今天适合买什么？
- AI 板块走势如何？
- 今天大盘情绪怎么样？
- 某只股票是否值得关注？
"""
            )
            question_box = gr.Textbox(label="请输入你的问题", placeholder="例如：今天适合买什么？")
            answer_btn = gr.Button("提交问题")
            answer_md = gr.Markdown("等待提问。")

        with gr.Tab("📜 历史报告"):
            history_md = gr.Markdown()

        with gr.Tab("🔌 接收端说明"):
            gr.Markdown(
                f"""
## OpenClaw 结果上传接口

三个机器人运行完后，把结果上传到：

POST /api/upload_report

请求头：

X-Upload-Token: {UPLOAD_TOKEN}

请求体需要包含：

agent：market / sector / stock  
date：例如 {today_str()}  
data：对应机器人生成的 JSON 内容

agent 可选值：

- market：大盘机器人
- sector：板块机器人
- stock：个股机器人
"""
            )

    outputs_all = [
        status_box,
        home_html,
        brief_md,
        market_table,
        breadth_table,
        market_index_plot,
        market_breadth_plot,
        market_volume_plot,
        sector_table,
        sector_change_plot,
        sector_fund_plot,
        stock_table,
        kline_plot,
        ma_plot,
        macd_plot,
        rsi_kdj_plot,
        stock_volume_plot,
        answer_md,
        history_md,
    ]

    refresh_btn.click(
        fn=refresh_dashboard,
        inputs=[],
        outputs=outputs_all,
    )

    summary_btn.click(
        fn=generate_and_refresh,
        inputs=[],
        outputs=outputs_all,
    )

    history_btn.click(
        fn=list_history_reports,
        inputs=[],
        outputs=history_md,
    )

    answer_btn.click(
        fn=qa_answer,
        inputs=question_box,
        outputs=answer_md,
    )

    demo.load(
        fn=refresh_dashboard,
        inputs=[],
        outputs=outputs_all,
    )


api_app = FastAPI()


@api_app.post("/api/upload_report")
async def upload_report(request: Request, x_upload_token: str = Header(default="")):
    if x_upload_token != UPLOAD_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid upload token")

    payload = await request.json()

    agent = payload.get("agent")
    report_date = payload.get("date") or today_str()
    data = payload.get("data")

    if agent not in ["market", "sector", "stock"]:
        raise HTTPException(status_code=400, detail="agent must be market, sector, or stock")

    if data is None:
        raise HTTPException(status_code=400, detail="missing data field")

    output_path = save_uploaded_report(agent, report_date, data)

    market_exists = (REPORT_DIR / f"{report_date}_market.json").exists()
    sector_exists = (REPORT_DIR / f"{report_date}_sector.json").exists()
    stock_exists = (REPORT_DIR / f"{report_date}_stock.json").exists()
    all_ready = market_exists and sector_exists and stock_exists

    message = f"{agent} report uploaded to {output_path.name}"

    if all_ready and report_date == today_str():
        try:
            run_summary_agent()
            message += "；三类结果已齐全，已尝试生成综合日报"
        except Exception:
            message += "；三类结果已齐全，但综合日报自动生成失败"

    return {
        "success": True,
        "message": message,
        "agent": agent,
        "date": report_date,
        "file": output_path.name,
        "all_ready": all_ready,
    }


@api_app.get("/api/status")
async def api_status():
    report_date = latest_available_date()
    return {
        "success": True,
        "date": report_date,
        "market": report_path("market", report_date).exists(),
        "sector": report_path("sector", report_date).exists(),
        "stock": report_path("stock", report_date).exists(),
    }


api_app = gr.mount_gradio_app(
    api_app,
    demo,
    path="/",
    auth=(UI_USER, UI_PASSWORD),
)


if __name__ == "__main__":
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=7861,
    )
