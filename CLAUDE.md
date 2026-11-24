# CLAUDE.md: context for AI coding assistants working in this repo

## What this is
Agent Checkpoint is my (Aman Abdul Salam) project for Intelligent Interactive Systems, Assignment 2 (Project Report), University of Birmingham. It is a research prototype comparing two approval prompts for a coding agent: a raw command prompt (baseline, like current coding agents) and a consequence card (what the action changes, can it be undone, would you notice, where data goes). Seeded harmful actions give ground truth, so decisions are scored with signal detection (hit rate, false alarms, d′, c) per block. It follows from my Assignment 1 literature review on approval fatigue at agent checkpoints.

## Assignment requirements (what the repo must support)
- Public repo with a README: prose word count near the top; project status (implemented / simulated / planned); tech stack; how to run or inspect; development record with links to commits; AI assistance with concrete examples of what I checked or changed.
- Never commit API keys. Reviewers supply their own via environment variables (GROQ_API_KEY or OPENAI_API_KEY; optional LIVE_MODEL).
- The report (separate, not in this repo) must not present simulated or planned features as implemented.

## Rubric (100)
- Design reasoning and scope /30: Weeks 1–4 concepts named and applied.
- Developed interaction /30: working interaction; honest labelling of simulated vs implemented.
- Architecture and technical reasoning /20: components, flows, the AI boundary.
- Development evidence and authorship /20: commit history that distinguishes original, reused and AI-assisted work; examples of reviewing and changing AI output.

## Rules for any change
- Run `python -m pytest -q` before every commit; all tests must pass.
- Small commits with clear messages. Keep the `Co-Authored-By: Claude` trailer on AI-assisted commits. Never rewrite or force-push history.
- Show me the diff before committing.
- Do not change `app/scenarios/*.json` or `app/analyser.py` rules unless I ask: they define the study's ground truth and the card's deliberate blind spots (auth-bypass edit rated low, typo-squat package).
- The consequence card is built by fixed rules, never by a model. The live model only proposes; nothing executes (dry run).
- Keep README status labels accurate. If something is untested, say so.
- Writing style for README and docs: plain, short sentences, British spelling, no em dashes.
- Never print, log or commit secrets.

## Architecture (short)
- `app/live_agent.py`: optional live model (OpenAI-compatible chat completions; Groq default), JSON-mode output validated by `parse_step`.
- `app/sessions.py`: session engine, interaction contracts (`AUTO_CLASSES` run without asking), "don't ask again", after-run report from the log.
- `app/analyser.py`: rule-based consequence analyser.
- `app/metrics.py`: signal-detection scoring.
- `app/main.py`: FastAPI routes; `static/`: plain HTML/CSS/JS UI.
- `data/`: JSONL decision log (gitignored).

## Current state and open items
- Groq retired `llama-3.3-70b-versatile` on 16 Aug 2026; live mode returned 404. Being fixed (replacement default `openai/gpt-oss-120b`; errors should show the provider's message).
- My own design change: the card should not show the agent's own description as analysis; show it labelled as an unchecked claim.
- README sections marked "Aman to complete" are mine to write; do not fill them in for me.
