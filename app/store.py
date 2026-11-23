"""Append-only JSON Lines log of sessions and decisions."""

from __future__ import annotations

import json
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("CHECKPOINT_DATA", Path(__file__).resolve().parent.parent / "data"))


def _append(name: str, rec: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def append_decision(rec: dict) -> None:
    _append("decisions.jsonl", rec)


def append_session(rec: dict) -> None:
    _append("sessions.jsonl", rec)


def read(name: str) -> list[dict]:
    p = DATA_DIR / name
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
