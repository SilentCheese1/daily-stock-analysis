#!/bin/bash

PROJECT="/Users/a1/Desktop/daily-stock-analysis-git"
LOG="$PROJECT/logs/market_daily.log"

cd "$PROJECT" || exit 1

echo "========== $(date) 开始运行大盘定时任务 ==========" >> "$LOG"

"$PROJECT/.venv/bin/python" agents/market_agent.py >> "$LOG" 2>&1

"$PROJECT/.venv/bin/python" agents/upload_report.py market >> "$LOG" 2>&1

echo "========== $(date) 大盘定时任务结束 ==========" >> "$LOG"
echo "" >> "$LOG"
