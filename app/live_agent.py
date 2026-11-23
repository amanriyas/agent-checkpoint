"""Optional live mode: a real language model proposes the agent's next action.

Nothing the model proposes is executed. Every action gets a dry-run result.
The model's output must match a JSON schema (Lecture 09); anything that does
not parse is treated as a malformed call and the session ends that step
(Lecture 12: the model proposes, the system disposes).

Provider: any OpenAI-compatible chat-completions endpoint. Set ONE of
GROQ_API_KEY or OPENAI_API_KEY in your environment (never commit keys).
"""

from __future__ import annotations

import json
import os

import httpx

SYSTEM_PROMPT = """You are a coding agent working in a Python web API repository called shop-api.
You act one step at a time. Reply with ONE JSON object and nothing else:
{"say": "<one short sentence to the user>",
 "action": {"tool": "bash"|"edit"|"read"|"delete",
            "command": "<shell command, for bash>",
            "path": "<file path, for edit/read/delete>",
            "summary": "<what the edit does, for edit>"} | null,
 "done": true|false}
Use "done": true and "action": null when the task is finished.
Results you receive are from a dry run: nothing really happens."""


def provider() -> tuple[str, str, str] | None:
    if os.getenv("GROQ_API_KEY"):
        return ("https://api.groq.com/openai/v1/chat/completions",
                os.environ["GROQ_API_KEY"], os.getenv("LIVE_MODEL", "llama-3.3-70b-versatile"))
    if os.getenv("OPENAI_API_KEY"):
        return ("https://api.openai.com/v1/chat/completions",
                os.environ["OPENAI_API_KEY"], os.getenv("LIVE_MODEL", "gpt-4o-mini"))
    return None


def available() -> bool:
    return provider() is not None


def parse_step(text: str) -> dict:
    """Validate the model's reply. Raises ValueError on a malformed proposal."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    data = json.loads(text)
    if not isinstance(data, dict) or "done" not in data:
        raise ValueError("missing 'done'")
    act = data.get("action")
    if act is not None:
        if act.get("tool") not in ("bash", "edit", "read", "delete"):
            raise ValueError(f"unknown tool {act.get('tool')!r}")
        if act["tool"] == "bash" and not act.get("command"):
            raise ValueError("bash action without command")
        if act["tool"] != "bash" and not act.get("path"):
            raise ValueError("file action without path")
    return data


def next_step(task: str, history: list[dict], post=None) -> dict:
    """Ask the model for its next step. `post` is injectable for tests."""
    url, key, model = provider()
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Task: {task}"}]
    for h in history:
        messages.append({"role": "assistant", "content": json.dumps(h["proposal"])})
        messages.append({"role": "user", "content": f"Result: {h['result']}"})
    body = {"model": model, "messages": messages, "temperature": 0.2,
            "response_format": {"type": "json_object"}}
    post = post or (lambda u, **kw: httpx.post(u, timeout=30, **kw))
    r = post(url, headers={"Authorization": f"Bearer {key}"}, json=body)
    r.raise_for_status()
    return parse_step(r.json()["choices"][0]["message"]["content"])
