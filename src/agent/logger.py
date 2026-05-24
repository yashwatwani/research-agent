# src/agent/logger.py — daily session logger
# writes one JSON line per interaction to data/logs/YYYY-MM-DD.log
# used by both test_agent.py (CLI) and main.py (Streamlit UI)
#
# log entry contains:
#   - timestamp, question, report, groundedness score, blocked status, context

import json
import os
from datetime import datetime


LOG_DIR = "data/logs"


def _log_path() -> str:
    # one file per day — data/logs/2026-05-24.log
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{date_str}.log")


def log_interaction(
    question: str,
    report: str,
    groundedness_score: float | None = None,
    blocked: bool = False,
    block_reason: str | None = None,
    context: str = "",
    source: str = "cli",        # "cli" or "ui"
) -> None:
    # appends a single JSON line to today's log file
    # creates data/logs/ directory if it doesn't exist

    os.makedirs(LOG_DIR, exist_ok=True)

    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "source": source,
        "question": question,
        "blocked": blocked,
        "block_reason": block_reason,
        "groundedness_score": groundedness_score,
        "report": report,
        "context": context[:3000] if context else "",   # cap to avoid huge log entries
    }

    with open(_log_path(), "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_today() -> list[dict]:
    # returns all interactions from today's log as a list of dicts
    # returns empty list if no log exists yet
    path = _log_path()
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def read_log(date_str: str) -> list[dict]:
    # read a specific day's log — date_str format: "2026-05-24"
    path = os.path.join(LOG_DIR, f"{date_str}.log")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]