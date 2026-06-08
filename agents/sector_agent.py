import json
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd


def normalize_number(value):
    """把 AkShare 返回的数值安全转成字符串。"""
    if pd.isna(value):
        return "未知"
    return str(value)


def try_eastmoney_industry():
    """
    尝试使用 AkShare 东方财富行业板块接口。
    """
    df = ak.stock_board_industry_name_em()

    if df is None or df.empty:
        raise ValueError("东方财富行业板块接口返回空数据")

    raw_columns = list(df.columns)

    if "涨跌幅" in df.columns:
        df = df.sort_values(by="涨跌幅", ascending=False)

    top_df = df.head(5)

    hot_sectors = []
    for _, row in top_df.iterrows():
        hot_sectors.append({
            "sector_name": normalize_number(row.get("板块名称", row.get("名称", "未知板块"))),
            "change_pct": normalize_number(row.get("涨跌幅", "未知")),
            "leading_stock": normalize_number(row.get("领涨股票", "未知")),
            "leading_stock_change_pct": normalize_number(row.get("领涨股票-涨跌幅", "未知")),
            "turnover_rate": normalize_number(row.get("换手率", "未知")),
            "source": "eastmoney"
        })

    return {
        "status": "success",
        "data_source": "AkShare-Eastmoney",
        "hot_sectors": hot_sectors,
        "raw_columns": raw_columns
    }


def try_ths_industry():
    """
    尝试使用 AkShare 同花顺行业板块接口。
    不同 AkShare 版本字段可能不同，所以这里做宽松处理。
    """
    if not hasattr(ak, "stock_board_industry_name_ths"):
        raise AttributeError("当前 AkShare 版本没有 stock_board_industry_name_ths 接口")

    df = ak.stock_board_industry_name_ths()

    if df is None or df.empty:
        raise ValueError("同花顺行业板块接口返回空数据")

    raw_columns = list(df.columns)

    # 尝试找到涨跌幅字段
    possible_change_cols = ["涨跌幅", "涨幅", "change_pct", "涨跌幅(%)"]
    change_col = None
    for col in possible_change_cols:
        if col in df.columns:
            change_col = col
            break

    if change_col:
        df = df.sort_values(by=change_col, ascending=False)

    top_df = df.head(5)

    hot_sectors = []
    for _, row in top_df.iterrows():
        # 尝试找到板块名称字段
        sector_name = (
            row.get("板块", None)
            or row.get("板块名称", None)
            or row.get("名称", None)
            or row.get("name", None)
            or "未知板块"
        )

        hot_sectors.append({
            "sector_name": normalize_number(sector_name),
            "change_pct": normalize_number(row.get(change_col, "未知")) if change_col else "未知",
            "leading_stock": normalize_number(row.get("领涨股", row.get("领涨股票", "未知"))),
            "leading_stock_change_pct": normalize_number(row.get("领涨股涨幅", "未知")),
            "turnover_rate": normalize_number(row.get("换手率", "未知")),
            "source": "ths"
        })

    return {
        "status": "success",
        "data_source": "AkShare-THS",
        "hot_sectors": hot_sectors,
        "raw_columns": raw_columns
    }


def get_sector_data():
    """
    多接口获取板块数据：
    1. 优先 AkShare-Eastmoney
    2. 失败后尝试 AkShare-THS
    """
    errors = []

    for fetcher in [try_eastmoney_industry, try_ths_industry]:
        try:
            result = fetcher()
            if result["status"] == "success" and result["hot_sectors"]:
                return result
        except Exception as e:
            errors.append(f"{fetcher.__name__}: {type(e).__name__}: {e}")

    return {
        "status": "failed",
        "data_source": "AkShare",
        "hot_sectors": [],
        "raw_columns": [],
        "error": "；".join(errors)
    }


def build_report():
    today = datetime.now().strftime("%Y-%m-%d")
    sector_data = get_sector_data()

    if sector_data["status"] == "success" and sector_data["hot_sectors"]:
        names = [item["sector_name"] for item in sector_data["hot_sectors"]]

        analysis = (
            "今日涨幅靠前的行业板块包括："
            + "、".join(names)
            + "。这些板块短线表现较活跃，可作为今日市场热点观察方向。"
        )

        risk = (
            "板块热点轮动较快，若部分板块短期涨幅过大，可能存在追高回落风险。"
            "需要结合成交量、资金持续性和大盘环境综合判断。"
        )

        suggestion = (
            "优先关注涨幅靠前且有领涨个股带动的板块，避免盲目追高；"
            "对高波动板块应控制仓位，等待回调或确认资金持续流入后再考虑。"
        )
    else:
        analysis = "今日板块数据获取失败或为空，暂不生成确定性板块判断。"
        risk = "数据源异常时不应直接依赖 AI 生成投资结论，避免出现编造数据。"
        suggestion = "建议稍后重试 AkShare 接口，或与组长确认是否需要备用数据源。"

    report = {
        "agent": "B",
        "module": "sector",
        "data_source": sector_data.get("data_source", "AkShare"),
        "date": today,
        "status": sector_data["status"],
        "hot_sectors": sector_data["hot_sectors"],
        "analysis": analysis,
        "risk": risk,
        "suggestion": suggestion,
        "raw_columns": sector_data.get("raw_columns", [])
    }

    if sector_data["status"] == "failed":
        report["error"] = sector_data.get("error", "")

    return report


def main():
    report = build_report()

    output_dir = Path("data/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{report['date']}_sector.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n已生成文件：{output_path}")


if __name__ == "__main__":
    main()
