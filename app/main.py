"""Agent Checkpoint: FastAPI app.

Run:  uvicorn app.main:app --reload   then open http://127.0.0.1:8000
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import live_agent, metrics
from .sessions import Engine
from .store import read

STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Agent Checkpoint")
engine = Engine()


class StartReq(BaseModel):
    participant: str = "anon"
    condition: str = "card"
    scenario: str = "fix_login_test"


class DecideReq(BaseModel):
    approved: bool
    dont_ask_again: bool = False
    ms: int | None = None


def _get(sid: str):
    s = engine.sessions.get(sid)
    if not s:
        raise HTTPException(404, "unknown session")
    return s


@app.get("/api/scenarios")
def scenarios():
    out = [{"id": k, "title": v["title"], "task": v["task"]} for k, v in engine.scenarios.items()]
    return {"scenarios": out, "live_available": live_agent.available()}


@app.post("/api/sessions")
def start(req: StartReq):
    try:
        s = engine.start(req.participant, req.condition, req.scenario)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))
    out = engine.advance(s)
    out.update(session=s.id, task=s.task, condition=s.condition, scenario=s.scenario_id)
    return out


@app.post("/api/sessions/{sid}/decide")
def decide(sid: str, req: DecideReq):
    s = _get(sid)
    try:
        return engine.decide(s, req.approved, req.dont_ask_again, req.ms)
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/sessions/{sid}/report")
def report(sid: str):
    return engine.report(_get(sid))


@app.get("/api/results")
def results():
    decisions = read("decisions.jsonl")
    by_cond = defaultdict(list)
    by_participant = defaultdict(list)
    for d in decisions:
        by_cond[d["condition"]].append(d)
        by_participant[(d["participant"], d["condition"])].append(d)
    # Blocks are formed per participant in the order they decided, so a
    # block trend reflects that person's repeated use.
    blocks = defaultdict(list)
    for (p, cond), ds in by_participant.items():
        for b in metrics.by_block(sorted(ds, key=lambda d: d["ts"])):
            b.update(participant=p, condition=cond)
            blocks[cond].append(b)
    misses = [d for d in decisions if d.get("harmful") and d["approved"]]
    return {
        "overall": metrics.score(decisions),
        "by_condition": {c: metrics.score(ds) for c, ds in by_cond.items()},
        "blocks": blocks,
        "missed_actions": [{"action": d["action"], "seeded": d.get("seeded"), "condition": d["condition"],
                            "auto": d.get("auto"), "participant": d["participant"]} for d in misses],
    }


@app.get("/api/export.csv", response_class=PlainTextResponse)
def export():
    rows = read("decisions.jsonl")
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return buf.getvalue()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
