#!/bin/bash

cd /home/chenyang1/daily-stock-analysis || exit 1

echo "===== 成员B：开始运行板块分析 Agent（新浪行业接口）====="
echo "当前时间：$(date '+%Y-%m-%d %H:%M:%S')"

echo ""
echo "===== 第一步：生成真实板块行情 JSON ====="
/home/chenyang1/daily-stock-analysis/.venv/bin/python agents/sector_agent.py

if [ $? -ne 0 ]; then
    echo "板块分析脚本运行失败"
    exit 1
fi

echo ""
echo "===== 第二步：上传板块结果到网站 ====="
/home/chenyang1/daily-stock-analysis/.venv/bin/python agents/upload_report.py sector

if [ $? -ne 0 ]; then
    echo "板块结果上传失败"
    exit 1
fi

echo ""
echo "===== 成员B板块分析已完成，并已上传网站 ====="
echo "如果上方显示 上传状态码：200，则说明板块结果已成功上传到网站。"
