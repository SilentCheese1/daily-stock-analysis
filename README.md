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

运行后，三个分析 Agent 会分别生成大盘、板块和个股分析 JSON 文件，并统一保存到 `data/reports/` 目录下。组长运行 `summary_agent.py` 后，系统会读取三份 JSON，生成综合分析结果，并将最终 HTML 日报保存为 `data/reports/日期_final_report.html`。展示时可在浏览器中打开该 HTML 文件查看完整日报。


## 三人分工

- A 同学：大盘分析 Agent，对应 `agents/market_agent.py`，飞书触发词：运行大盘
- B 同学：板块分析 Agent，对应 `agents/sector_agent.py`，飞书触发词：运行板块
- C 同学：个股分析 Agent，对应 `agents/stock_agent.py`，飞书触发词：运行个股
- 组长：汇总 Agent，对应 `agents/summary_agent.py`，飞书触发词：运行汇总

## 重要提醒

数据源统一使用 akshare
