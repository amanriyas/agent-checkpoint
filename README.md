# Agent Checkpoint

A research prototype for studying how people supervise a coding agent through approval prompts. It compares a raw command prompt, like today's coding agents use, with a consequence card that states what an action changes, whether it can be undone and whether you would notice. Every decision is scored against seeded harmful actions.

Module: Intelligent Interactive Systems, Assignment 2 (Project Report). Author: Aman Abdul Salam.
README prose word count: **about 1,100** (code, commands and tables of file names not counted).

## Project status

| Part | Status |
|---|---|
| Session runner: an agent works through a task and pauses for approval | **Implemented** |
| Two approval designs: raw command prompt and consequence card | **Implemented** |
| Rule-based consequence analyser (object, side effects, undo, scope, risk) | **Implemented** |
| Three scripted tasks with 30 approval points, 9 seeded harmful actions | **Implemented; the agent is simulated** (scripted steps, nothing executes) |
| Decision log (JSON Lines, CSV export) and signal-detection scoring (hit rate, false alarms, d′, c, per-block trend) | **Implemented** |
| After-run report built from the log, shown beside the agent's own claim | **Implemented** |
| Live mode: a real model proposes actions (dry run, schema-validated, harmful actions seeded in) | **Implemented, partly tested**: unit tests with a fake model; run against Groq `openai/gpt-oss-120b` on 24 Nov 2026. Sessions often end early because the model makes a malformed call, which the validator rejects |
| Multi-day sessions with the same people, varied card designs (Vance et al., 2018), real sandbox execution | **Planned** |

Nothing in this prototype runs a real command. "Results" shown in the transcript come from the scenario files (scripted mode) or are `[dry run]` placeholders (live mode).

## Technology stack

- **Python 3.11+, FastAPI, Uvicorn**: the API, session engine and static file server.
- **Plain HTML, CSS and JavaScript**: the interface. No build step, so a reviewer can run it with one command.
- **Rule-based analyser** (`app/analyser.py`): deliberately not a language model, so the card never shows a generated claim.
- **pytest**: 17 tests covering the analyser (including its known blind spots), the scoring and full sessions.
- **Optional live model**: any OpenAI-compatible endpoint. Groq (`openai/gpt-oss-120b`) by default, OpenAI (`gpt-4o-mini`) as a fallback; override with `LIVE_MODEL`.
- **AI tool used to build it**: Claude (Anthropic); see [AI assistance](#ai-assistance).
- Undecided: whether a future version should let the analyser call a model for unrecognised commands, with its output marked as a claim.

## Running or inspecting the work

Windows PowerShell:

```powershell
git clone https://github.com/amanriyas/agent-checkpoint.git
cd agent-checkpoint
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process Bypass` first. It only lasts for that window.

macOS or Linux:

```bash
git clone https://github.com/amanriyas/agent-checkpoint.git
cd agent-checkpoint
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run the tests: `python -m pytest -q`

Optional live mode, using your own key (never commit it). Set it in the same window, then start the server:

```powershell
$env:GROQ_API_KEY = "..."      # or $env:OPENAI_API_KEY = "..."
uvicorn app.main:app
```

On macOS or Linux use `export GROQ_API_KEY=...` instead. The start page offers a live task only when a key is set.

Where to look:

- `app/scenarios/*.json`: the three scripted tasks. Each harmful step has `"harmful": true` and a `seeded` note saying why.
- `app/analyser.py`: every rule behind the consequence card.
- `app/sessions.py`: interaction contracts (which actions run without asking), the session loop and the after-run report.
- `app/metrics.py`: signal-detection scoring.
- `data/decisions.jsonl`: created on first use; one line per decision. Also downloadable as CSV from the Results page.
- `docs/screenshots/`: screenshots from a scripted browser walkthrough.
- `docs/figures/`: the report's system diagram and storyboards. `tools/` holds the scripts that made them (Playwright).

## Development record

Grouped by stage. "Origin" says whose idea each decision was: **Aman** (mine), **AI** (proposed by the assistant), or **AI → Aman** (proposed by the assistant, then checked or changed by me).

1. **Scope from Assignment 1** (origin: Aman). The literature review ended with a question: does detection at approval checkpoints decline with use, and is that a looser criterion or lost sensitivity? The build is the smallest system that can measure this: two prompt designs, seeded harmful actions with ground truth, and scoring. Real execution and multi-day studies are planned, not built.
2. **Rules, not a model, behind the card** (`app/analyser.py`; origin: AI). A model-written card would be one more fluent claim that can be wrong (Lecture 08). The analyser is a fixed rule table that says "unknown" when no rule matches. Unit tests pin down two blind spots: a typo-squatted package and an auth-bypass edit both get a low or medium card.
3. **Scenarios that do not make the card an oracle** (`app/scenarios/`; origin: AI). Some harmful actions look routine on the card (auth edit, typo-squat). Some safe actions look alarming (deleting `build/`, pushing a release to `main`, uploading to the internal artefact store). The comparison is then about reading the card, not about following a red label.
4. **Fewer prompts by contract** (`AUTO_CLASSES` in `app/sessions.py`; origin: AI). Reads and test runs run without asking and are reported in the transcript (Lecture 13, contract 4). Prompting for them would only add the volume that leads to reflex approval.
5. **"Don't ask again"** (origin: AI). The raw prompt offers it for every class, as real tools do. The card offers it only for low-risk actions that can be undone. Approvals granted this way are logged as `auto` and count as misses when harmful.
6. **After-run report from the log** (`Engine.report`; origin: AI, following Lectures 12–13). Each scenario ends with the agent claiming success. The report sets that claim beside what the log shows: done, refused, assumed and cannot-undo.
7. **Scoring** (`app/metrics.py`; origin: Aman's A1 question, implemented by AI). Hits, misses, false alarms, d′ and c with a log-linear correction, overall and in blocks of 8 decisions per participant.
8. **Live mode** (`app/live_agent.py`; origin: Aman asked for it, implemented by AI). Model output must parse as a fixed JSON schema or the session stops (Lecture 09). Two known-harmful actions are mixed in so live sessions still have ground truth; model actions are logged as unlabelled. Groq retired `llama-3.3-70b-versatile` on 16 Aug 2026, so the default is now `openai/gpt-oss-120b`. It proposes actions as native tool calls, because in JSON mode it kept trying to call tools and failing. Provider errors are shown in the session.
9. **Fixes after the first browser walkthrough** (origin: AI). The card heading read "The agent wants to / Uploads…", now "If you approve, this". Test runs were labelled "read-only", now "test run". The Results page now states its numbers are not study results.

> **Aman to complete before submission** (in your own words, with commit links):
> - Which of the AI-originated decisions above you reviewed, kept or changed, and why. Update each "origin" accordingly.
> - What you changed after trying it yourself.
> - The live-mode check with your own Groq key: did it run, and what did the model propose?

## AI assistance

- **Tool:** Claude (Anthropic), in a chat-based coding workspace.
- **Asked for:** a prototype of the design from my Assignment 1 literature review; the analyser, session engine, scoring and interface; tests; a first draft of this README; screenshots for the report.
- **Authorship in the history:** commits written by the assistant are authored as "Claude (AI assistant)". Commits under my name are my own changes.
- **Checks run so far:** 17 automated tests; a scripted browser walkthrough of all three tasks in both conditions, whose screenshots are in `docs/screenshots/`.
- > **Aman to complete:** one or two concrete examples of a suggestion you rejected or changed, and what you checked by hand (for example, reading each seeded action's label against the card it produces).

## Additional files

None outside this repository. The report is submitted separately and links here.
