import json

import akshare as ak
import pandas as pd

from common import today_str, save_report


def safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def get_index_analysis():
    """
    获取上证指数、深证成指、创业板指的实时行情。
    数据源：AkShare 新浪财经指数实时行情接口。
    """
    target_indexes = {
        "上证指数": "sh000001",
        "深证成指": "sz399001",
        "创业板指": "sz399006",
    }

    try:
        df = ak.stock_zh_index_spot_sina()
    except Exception as e:
        return {
            name: {
                "code": code,
                "latest": None,
                "change_pct": None,
                "status": f"新浪指数数据获取失败：{e}"
            }
            for name, code in target_indexes.items()
        }

    result = {}

    for name, code in target_indexes.items():
        row = df[df["代码"].astype(str) == code]

        if row.empty:
            result[name] = {
                "code": code,
                "latest": None,
                "change_pct": None,
                "status": "未匹配到指数数据"
            }
            continue

        row = row.iloc[0]

        result[name] = {
            "code": str(row.get("代码", code)),
            "latest": safe_float(row.get("最新价")),
            "change_pct": safe_float(row.get("涨跌幅")),
            "change_amount": safe_float(row.get("涨跌额")),
            "volume": safe_float(row.get("成交量")),
            "amount": safe_float(row.get("成交额")),
            "status": "success"
        }

    return result


def get_market_breadth():
    """
    获取全 A 股上涨家数、下跌家数，用于判断市场情绪。
    数据源：AkShare 新浪财经 A 股实时行情接口。
    """
    try:
        df = ak.stock_zh_a_spot()
    except Exception as e:
        return {
            "up_count": None,
            "down_count": None,
            "flat_count": None,
            "avg_change_pct": None,
            "market_sentiment": "未知",
            "status": f"新浪A股行情获取失败：{e}"
        }

    if "涨跌幅" not in df.columns:
        return {
            "up_count": None,
            "down_count": None,
            "flat_count": None,
            "avg_change_pct": None,
            "market_sentiment": "未知",
            "status": "未找到涨跌幅字段"
        }

    changes = pd.to_numeric(df["涨跌幅"], errors="coerce").dropna()

    up_count = int((changes > 0).sum())
    down_count = int((changes < 0).sum())
    flat_count = int((changes == 0).sum())
    avg_change_pct = round(float(changes.mean()), 2) if len(changes) > 0 else None

    if up_count > down_count * 1.3 and avg_change_pct is not None and avg_change_pct > 0:
        sentiment = "偏强"
    elif down_count > up_count * 1.3 and avg_change_pct is not None and avg_change_pct < 0:
        sentiment = "偏弱"
    else:
        sentiment = "中性震荡"

    return {
        "up_count": up_count,
        "down_count": down_count,
        "flat_count": flat_count,
        "avg_change_pct": avg_change_pct,
        "market_sentiment": sentiment,
        "status": "success"
    }


def build_summary(index_analysis, market_breadth):
    index_texts = []

    for name, info in index_analysis.items():
        latest = info.get("latest")
        change_pct = info.get("change_pct")

        if latest is None or change_pct is None:
            index_texts.append(f"{name}数据暂未获取成功")
        else:
            if change_pct > 0:
                direction = "上涨"
            elif change_pct < 0:
                direction = "下跌"
            else:
                direction = "持平"

            index_texts.append(
                f"{name}最新点位为{latest}，涨跌幅为{change_pct}%，表现为{direction}"
            )

    up_count = market_breadth.get("up_count")
    down_count = market_breadth.get("down_count")
    sentiment = market_breadth.get("market_sentiment", "未知")

    if up_count is not None and down_count is not None:
        breadth_text = (
            f"全市场上涨家数约为{up_count}家，下跌家数约为{down_count}家，"
            f"市场情绪为{sentiment}。"
        )
    else:
        breadth_text = f"涨跌家数暂未获取成功，市场情绪为{sentiment}。"

    summary = "；".join(index_texts) + "。" + breadth_text

    if sentiment == "偏强":
        risk = "市场整体表现较强，但短线快速上涨后仍需关注成交量能否持续放大。"
        suggestion = "可适当关注强势方向，但不宜追高，优先选择趋势稳定、成交量配合的标的。"
    elif sentiment == "偏弱":
        risk = "市场下跌家数较多，短线风险偏高，需防范指数继续回调。"
        suggestion = "建议控制仓位，以观察为主，等待市场情绪修复后再考虑参与。"
    else:
        risk = "市场分化明显，热点持续性仍需观察。"
        suggestion = "建议轻仓参与，关注低位放量、基本面稳定和资金流入较好的方向。"

    return summary, risk, suggestion


def build_report():
    index_analysis = get_index_analysis()
    market_breadth = get_market_breadth()
    summary, risk, suggestion = build_summary(index_analysis, market_breadth)

    report = {
        "agent": "market",
        "date": today_str(),
        "module": "大盘分析",
        "data_source": "AkShare-Sina",
        "index_analysis": index_analysis,
        "market_breadth": market_breadth,
        "summary": summary,
        "risk": risk,
        "suggestion": suggestion
    }

    return report


if __name__ == "__main__":
    result = build_report()
    save_report("market", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
