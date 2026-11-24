"""Optional live mode: a real language model proposes the agent's next action.

Nothing the model proposes is executed. Every action gets a dry-run result.
The model's tool call must match a fixed schema (Lecture 09); anything that does
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
You act one step at a time: call exactly ONE of the tools bash, edit, read or delete,
or call finish when the task is complete. You cannot see any file until you read it,
so start by reading code or running the tests. Only call finish when the results
so far show the task is done. Every result is from a dry run: nothing really happens
and there is no output. Do not repeat an action; take the next step you would take
if it had worked."""


def _tool(name: str, desc: str, **props) -> dict:
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
        "required": [k for k in props if k != "say"]}}}


# Native tool calls, not free-text JSON: reasoning models such as gpt-oss try to
# call tools anyway and fail JSON mode when they are not offered any.
TOOLS = [
    _tool("bash", "Run one shell command.", say="One short sentence to the user.", command="The shell command."),
    _tool("edit", "Edit a file.", say="One short sentence to the user.", path="File path.",
          summary="What the edit does."),
    _tool("read", "Read one file. To list a folder, use bash with ls.", say="One short sentence to the user.", path="File path, never empty."),
    _tool("delete", "Delete a file or folder.", say="One short sentence to the user.", path="Path."),
    _tool("finish", "The task is complete.", say="What you did, for the user."),
]


# Groq error codes for a generation the model got wrong (seen with gpt-oss).
GENERATION_ERRORS = ("tool_use_failed", "output_parse_failed", "json_validate_failed")


def _for_model(result: str) -> str:
    """Plain result text for the model. gpt-oss often fails to produce a tool
    call after a bare "The user refused this action." (tested on Groq)."""
    if "refused" in result:
        return "Not run: the user refused this action. Choose a different next step."
    if result.startswith("[dry run]"):
        return "Dry run: not executed, no output. Assume it worked."
    return result


def to_proposal(message: dict) -> str:
    """Turn a tool call into the proposal JSON that parse_step validates."""
    calls = message.get("tool_calls") or []
    if not calls:
        return message.get("content") or ""
    fn = calls[0]["function"]
    args = json.loads(fn.get("arguments") or "{}")
    say = args.pop("say", "")
    if fn["name"] == "finish":
        return json.dumps({"say": say, "action": None, "done": True})
    return json.dumps({"say": say, "action": dict(args, tool=fn["name"]), "done": False})


def provider() -> tuple[str, str, str] | None:
    if os.getenv("GROQ_API_KEY"):
        return ("https://api.groq.com/openai/v1/chat/completions",
                os.environ["GROQ_API_KEY"], os.getenv("LIVE_MODEL", "openai/gpt-oss-120b"))
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
            raise ValueError(f"{act['tool']} action without path")
    return data


def next_step(task: str, history: list[dict], post=None) -> dict:
    """Ask the model for its next step. `post` is injectable for tests."""
    url, key, model = provider()
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Task: {task}"}]
    for i, h in enumerate(history):
        act = dict(h["proposal"]["action"])
        call = {"id": f"call_{i}", "type": "function",
                "function": {"name": act.pop("tool"), "arguments": json.dumps(act)}}
        messages.append({"role": "assistant", "content": None, "tool_calls": [call]})
        messages.append({"role": "tool", "tool_call_id": f"call_{i}", "content": _for_model(h["result"])})
    body = {"model": model, "messages": messages, "temperature": 0.2,
            "tools": TOOLS, "tool_choice": "required"}
    post = post or (lambda u, **kw: httpx.post(u, timeout=30, **kw))
    r = post(url, headers={"Authorization": f"Bearer {key}"}, json=body)
    if r.status_code == 400 and any(c in r.text for c in GENERATION_ERRORS):
        # The provider rejected a malformed generation before we saw it: ask once more.
        r = post(url, headers={"Authorization": f"Bearer {key}"}, json=body)
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Show the provider's own message (e.g. a retired model), not just the status.
        raise RuntimeError(f"{model}: HTTP {r.status_code}: {r.text[:300]}") from e
    choice = r.json()["choices"][0]
    # Reasoning models (gpt-oss) put their reasoning in a separate field, which
    # is ignored. The reply can be empty if the model ran out of tokens.
    content = to_proposal(choice["message"])
    if not content:
        raise RuntimeError(f"{model}: empty reply (finish_reason={choice.get('finish_reason')})")
    return parse_step(content)
