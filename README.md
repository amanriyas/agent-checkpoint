# Agent Checkpoint

A research prototype for studying how people supervise a coding agent through approval prompts. It compares a raw command prompt, like today's coding agents use, with a consequence card that states what an action changes, whether it can be undone and whether you'd notice. I score every decision against seeded harmful actions.

Module: Intelligent Interactive Systems, Assignment 2 (Project Report). Author: Aman Abdul Salam.
README prose word count: **about 1,500** (code blocks, inline code and URLs not counted).

## Project status

| Part | Status |
|---|---|
| Session runner: an agent works through a task and pauses for approval | **Implemented** |
| Two approval designs: raw command prompt and consequence card | **Implemented** |
| Rule-based consequence analyser (object, side effects, undo, scope, risk) | **Implemented** |
| Three scripted tasks with 30 approval points, 9 seeded harmful actions | **Implemented; the agent is simulated** (scripted steps, nothing executes) |
| Decision log (JSON Lines, CSV export) and signal-detection scoring (hit rate, false alarms, d′, c, per-block trend) | **Implemented** |
| After-run report built from the log, shown beside the agent's own claim | **Implemented** |
| Live mode: a real model proposes actions (dry run, schema-validated, harmful actions seeded in) | **Implemented, partly tested**: unit tests with a fake model; run against Groq `openai/gpt-oss-120b` on 24 Nov 2026. Every live session so far ended early because the model made a malformed call, which the validator rejects |
| Multi-day sessions with the same people, varied card designs (Vance et al., 2018), real sandbox execution | **Planned** |

Nothing in this prototype runs a real command, so it's safe to try. "Results" shown in the transcript come from the scenario files (scripted mode) or are `[dry run]` placeholders (live mode).

## Technology stack

- **Python 3.11+, FastAPI, Uvicorn**: the API, session engine and static file server.
- **Plain HTML, CSS and JavaScript**: the interface. No build step, so you can run it with one command.
- **Rule-based analyser** (`app/analyser.py`): I deliberately didn't use a language model here, so the card never shows a generated claim.
- **pytest**: 17 tests covering the analyser (including its known blind spots), the scoring and full sessions.
- **Optional live model**: any OpenAI-compatible endpoint. Groq (`openai/gpt-oss-120b`) by default, OpenAI (`gpt-4o-mini`) as a fallback (untested); override with `LIVE_MODEL`.
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

macOS or Linux (untested):

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

On macOS or Linux use `export GROQ_API_KEY=...` instead. You'll only see a live task on the start page when a key is set.

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

1. **Scope from Assignment 1** ([4182520](https://github.com/amanriyas/agent-checkpoint/commit/4182520); origin: Aman). The literature review ended with a question: does detection at approval checkpoints decline with use, and is that a looser criterion or lost sensitivity? I built the smallest system that can measure this: two prompt designs, seeded harmful actions with ground truth, and scoring. Real execution and multi-day studies are planned, not built.
2. **Rules, not a model, behind the card** (`app/analyser.py`, [9841ca1](https://github.com/amanriyas/agent-checkpoint/commit/9841ca1); origin: AI → Aman, changed in item 10). A model-written card would just be one more fluent claim that can be wrong (Lecture 08), and I didn't want that. The analyser is a fixed rule table that says "unknown" when no rule matches. Unit tests ([3dd303f](https://github.com/amanriyas/agent-checkpoint/commit/3dd303f)) pin down two blind spots: a typo-squatted package and an auth-bypass edit both get a low or medium card.
3. **Scenarios that don't make the card an oracle** (`app/scenarios/`, [248e276](https://github.com/amanriyas/agent-checkpoint/commit/248e276); origin: AI). Some harmful actions look routine on the card (auth edit, typo-squat). And some safe actions look alarming (deleting `build/`, pushing a release to `main`, uploading to the internal artefact store). That way the comparison is about reading the card, not following a red label.
4. **Fewer prompts by contract** (`AUTO_CLASSES` in `app/sessions.py`, [97d240a](https://github.com/amanriyas/agent-checkpoint/commit/97d240a); origin: AI). Reads and test runs run without asking and are reported in the transcript (Lecture 13, contract 4). Asking about them would only add the volume that leads to reflex approval, and that's the problem I'm studying.
5. **"Don't ask again"** ([97d240a](https://github.com/amanriyas/agent-checkpoint/commit/97d240a); origin: AI). The raw prompt offers it for every class, as real tools do. The card only offers it for low-risk actions you can undo. Approvals granted this way are logged as `auto` and count as misses when harmful.
6. **After-run report from the log** (`Engine.report`, [97d240a](https://github.com/amanriyas/agent-checkpoint/commit/97d240a); origin: AI, following Lectures 12–13). Each scenario ends with the agent claiming it's done. The report sets that claim beside what the log shows: done, refused, assumed and cannot-undo.
7. **Scoring** (`app/metrics.py`, [d2f8563](https://github.com/amanriyas/agent-checkpoint/commit/d2f8563); origin: Aman's A1 question, implemented by AI). Hits, misses, false alarms, d′ and c with a log-linear correction, overall and in blocks of 8 decisions per participant.
8. **Live mode** (`app/live_agent.py`, [075e2b2](https://github.com/amanriyas/agent-checkpoint/commit/075e2b2); origin: Aman asked for it, implemented by AI). Model output must parse as a fixed JSON schema or the session stops (Lecture 09). Two known-harmful actions are mixed in so live sessions still have ground truth; model actions are logged as unlabelled. Groq retired `llama-3.3-70b-versatile` on 16 Aug 2026, so the default is now `openai/gpt-oss-120b`. It now proposes actions as native tool calls; in JSON mode it kept trying to call tools anyway and failing. Provider errors are shown in the session.
9. **Fixes after the first browser walkthrough** ([29b8adc](https://github.com/amanriyas/agent-checkpoint/commit/29b8adc); origin: AI). The interface itself was built in [c0de967](https://github.com/amanriyas/agent-checkpoint/commit/c0de967). The card heading read "The agent wants to / Uploads…", now "If you approve, this". Test runs were labelled "read-only", now "test run". The Results page now says its numbers aren't study results.

10. **The agent's description is a claim, not analysis** ([c573239](https://github.com/amanriyas/agent-checkpoint/commit/c573239); origin: AI → Aman). While making the report figures, the assistant pointed out that the card listed the agent's own edit summary ("Simplify verify_token") among its effects, so the agent's words looked like the checkpoint's analysis. I checked this in the browser, agreed, applied the change by hand and committed it. The assistant then added a test ([fef3cea](https://github.com/amanriyas/agent-checkpoint/commit/fef3cea)).
11. **Live mode against a real API** ([32b1dde](https://github.com/amanriyas/agent-checkpoint/commit/32b1dde); origin: AI). Groq had retired the original model, so live sessions ended at once with a 404. The assistant ran the check through the API with my Groq key. `openai/gpt-oss-120b` proposed real steps, mostly `ls -R` and reading files, and the seeded harmful actions (CI edit, force push, secrets upload) reached the card as intended. Every session still ended early on a malformed model call. The validator rejected it, which is what it's there for.
12. **Setup steps fixed for Windows** ([5ace61a](https://github.com/amanriyas/agent-checkpoint/commit/5ace61a); origin: AI). The old steps failed in PowerShell, and `set GROQ_API_KEY=...` silently left live mode off.
13. **Screenshots and storyboards refreshed** ([a84a852](https://github.com/amanriyas/agent-checkpoint/commit/a84a852); origin: AI). They now show the card from item 10. The first screenshots came with the README in [21000f6](https://github.com/amanriyas/agent-checkpoint/commit/21000f6), and the system diagram and storyboards in [c7e298e](https://github.com/amanriyas/agent-checkpoint/commit/c7e298e).
14. **Rules for the assistant** (`CLAUDE.md`, [9708864](https://github.com/amanriyas/agent-checkpoint/commit/9708864)). It sets the rules Claude Code worked under: run the tests before every commit, show me the diff, never commit or print keys, don't edit the scenarios or analyser rules unless I ask, and don't write my reflections.

## AI assistance

- **Tool:** Claude (Anthropic), in a chat-based coding workspace.
- **Asked for:** a prototype of the design from my Assignment 1 literature review; the analyser, session engine, scoring and interface; tests; a first draft of this README; screenshots for the report.
- **Authorship in the history:** early commits written by the assistant are authored as "Claude (AI assistant)". c573239 I applied by hand after the assistant flagged the problem (item 10). The later commits 32b1dde, fef3cea, 5ace61a and a84a852 are under my name because I ran them, but their content was written by the assistant; their messages lack a `Co-Authored-By` line, so this list is the record.
- **Checks run so far:** 17 automated tests; a scripted browser walkthrough of all three tasks in both conditions, whose screenshots are in `docs/screenshots/`.
- **Changed or decided by me:** I ran live mode myself on its first real run, found it failing with a 404 and reported it, which is how the retired Groq model was found (item 11). I applied and checked the card change in item 10 after the assistant flagged the problem.
- **Checked by me:** I've used the app myself in the browser. I made every commit from c573239 on myself; for each one containing the assistant's work, the assistant showed me the diff first and the tests passed.

## Additional files

There aren't any outside this repository. The report is submitted separately and links here.
