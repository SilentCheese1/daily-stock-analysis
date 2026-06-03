# 每日股票分析数字员工系统

基于 OpenClaw 与飞书机器人的三智能体协作系统，包含大盘分析、板块分析、个股分析和 HTML 汇总展示。

## 运行顺序

```bash
cd openclaw_pkg
python agents/market_agent.py
python agents/sector_agent.py
python agents/stock_agent.py
python agents/summary_agent.py
```

运行后，JSON 会保存在 `data/reports/`，最终 HTML 日报会保存在 `data/reports/日期_final_report.html`。

## 三人分工

- A 同学：大盘分析 Agent，对应 `agents/market_agent.py`，飞书触发词：运行大盘
- B 同学：板块分析 Agent，对应 `agents/sector_agent.py`，飞书触发词：运行板块
- C 同学：个股分析 Agent，对应 `agents/stock_agent.py`，飞书触发词：运行个股
- 组长：汇总 Agent，对应 `agents/summary_agent.py`，飞书触发词：运行汇总

## 重要提醒

数据源统一使用 akshare
