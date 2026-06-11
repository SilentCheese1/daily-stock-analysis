import json
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def safe_value(value, default="数据暂缺"):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass

    text = str(value).strip()
    if text == "" or text.lower() in ["nan", "none", "null"]:
        return default
    return text


def to_float(value):
    try:
        if value is None:
            return None
        text = str(value).replace("%", "").replace(",", "").strip()
        if text == "" or text.lower() in ["nan", "none", "null"]:
            return None
        return float(text)
    except Exception:
        return None


def fmt_pct(value):
    num = to_float(value)
    if num is None:
        return safe_value(value, "数据暂缺")
    return f"{num:.2f}"


def fmt_amount_wan(value):
    """
    新浪板块接口里的“总成交额”单位是万元。
    这里把它格式化成更适合展示的文字。
    """
    num = to_float(value)
    if num is None:
        return "成交额数据暂缺"

    if abs(num) >= 10000:
        return f"{num / 10000:.2f}亿元"
    return f"{num:.2f}万元"


def get_sina_sector_data():
    """
    获取新浪行业板块实时行情。
    AKShare 接口：stock_sector_spot(indicator="新浪行业")
    常见字段：
    label、板块、公司家数、平均价格、涨跌额、涨跌幅、总成交量、总成交额、
    股票代码、个股-涨跌幅、个股-当前价、个股-涨跌额、股票名称
    """
    df = ak.stock_sector_spot(indicator="新浪行业")

    if df is None or df.empty:
        raise RuntimeError("AkShare 新浪行业板块接口返回为空")

    print("新浪行业板块字段：", list(df.columns))
    return df


def build_sector_report():
    date = today_str()

    df = get_sina_sector_data().copy()

    if "涨跌幅" not in df.columns:
        raise RuntimeError(f"新浪行业板块数据缺少“涨跌幅”字段，当前字段：{list(df.columns)}")

    df["涨跌幅_数值"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
    df = df.sort_values("涨跌幅_数值", ascending=False)

    top_df = df.head(5)

    hot_sectors = []

    for rank, (_, row) in enumerate(top_df.iterrows(), start=1):
        sector_name = safe_value(
            row.get("板块") or row.get("名称") or row.get("name"),
            f"板块{rank}"
        )

        change_pct = fmt_pct(row.get("涨跌幅"))
        avg_price = safe_value(row.get("平均价格"), "数据暂缺")
        price_change = safe_value(row.get("涨跌额"), "数据暂缺")
        total_volume = safe_value(row.get("总成交量"), "数据暂缺")
        total_amount = row.get("总成交额")

        leading_stock = safe_value(row.get("股票名称"), "数据暂缺")
        leading_stock_code = safe_value(row.get("股票代码"), "数据暂缺")
        leading_stock_change_pct = fmt_pct(row.get("个股-涨跌幅"))
        leading_stock_price = safe_value(row.get("个股-当前价"), "数据暂缺")

        amount_text = fmt_amount_wan(total_amount)

        # 新浪接口没有真实“主力净流入”，这里用真实成交额表达资金活跃度，避免编造主力资金。
        fund_flow = f"总成交额 {amount_text}（新浪板块口径）"

        hot_reason = (
            f"{sector_name}板块今日涨跌幅为 {change_pct}%，"
            f"板块平均价格为 {avg_price}，涨跌额为 {price_change}。"
            f"领涨股为 {leading_stock}，个股涨跌幅为 {leading_stock_change_pct}%，"
            f"当前价为 {leading_stock_price}。"
            f"板块总成交量为 {total_volume}，总成交额为 {amount_text}。"
        )

        hot_sectors.append({
            "rank": rank,

            # 网站展示字段
            "name": sector_name,
            "change_pct": change_pct,
            "fund_flow": fund_flow,
            "hot_reason": hot_reason,

            # 兼容字段
            "sector_name": sector_name,
            "leading_stock": leading_stock,
            "leading_stock_code": leading_stock_code,
            "leading_stock_change_pct": leading_stock_change_pct,
            "leading_stock_price": leading_stock_price,
            "avg_price": avg_price,
            "price_change": price_change,
            "total_volume": total_volume,
            "total_amount": amount_text,
            "source": "AkShare-Sina"
        })

    sector_names = [item["name"] for item in hot_sectors]

    analysis = (
        "今日新浪行业板块涨幅靠前的方向包括："
        + "、".join(sector_names)
        + "。这些板块在涨跌幅和成交额维度上表现较活跃，可作为当日市场热点观察方向。"
    )

    risk = (
        "板块涨幅靠前说明短线热度较高，但也可能存在追高风险。"
        "由于新浪板块接口不直接提供主力净流入字段，本报告使用板块总成交额辅助判断资金活跃度，"
        "建议结合大盘走势、成交量变化和领涨股持续性进一步判断。"
    )

    suggestion = (
        "优先关注涨幅靠前、成交额较高、领涨股表现较强的行业板块；"
        "对于短线涨幅过大但后续成交额不能持续放大的板块，应控制仓位并等待回调确认。"
    )

    report = {
        "agent": "B",
        "module": "sector",
        "data_source": "AkShare-Sina",
        "date": date,
        "status": "success",
        "hot_sectors": hot_sectors,
        "analysis": analysis,
        "risk": risk,
        "suggestion": suggestion,
        "raw_columns": list(df.columns)
    }

    return report


def main():
    report = build_sector_report()

    output_file = REPORT_DIR / f"{report['date']}_sector.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n已生成文件：{output_file}")


if __name__ == "__main__":
    main()
