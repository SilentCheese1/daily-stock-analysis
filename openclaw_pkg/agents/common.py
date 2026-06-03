import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def save_report(agent_name: str, data: dict) -> Path:
    date = data.get("date") or today_str()
    path = REPORT_DIR / f"{date}_{agent_name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_report(agent_name: str, date: str | None = None) -> dict | None:
    date = date or today_str()
    path = REPORT_DIR / f"{date}_{agent_name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
