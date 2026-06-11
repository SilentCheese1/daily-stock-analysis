import json
import sys
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "reports"

UPLOAD_URL = "http://127.0.0.1:7861/api/upload_report"
UPLOAD_TOKEN = "stock-demo-token"


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def upload_report(agent_name):
    date = today_str()
    json_path = REPORT_DIR / f"{date}_{agent_name}.json"

    if not json_path.exists():
        print(f"❌ 找不到报告文件：{json_path}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    payload = {
        "agent": agent_name,
        "date": date,
        "data": data,
    }

    response = requests.post(
        UPLOAD_URL,
        headers={
            "Content-Type": "application/json",
            "X-Upload-Token": UPLOAD_TOKEN,
        },
        json=payload,
        timeout=30,
    )

    print("上传状态码：", response.status_code)
    print("上传返回：", response.text)

    return response.status_code == 200


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 agents/upload_report.py market/sector/stock")
        sys.exit(1)

    agent_name = sys.argv[1]
    ok = upload_report(agent_name)

    if not ok:
        sys.exit(1)
