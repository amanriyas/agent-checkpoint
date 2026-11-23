// Agent Checkpoint front end. Plain JS, no build step.
const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let session = null;
let shownAt = 0;

const REVERSIBILITY = { undoable: "Can be undone", hard_to_undo: "Hard to undo", irreversible: "Cannot be undone" };
const REV_CLASS = { undoable: "b-low", hard_to_undo: "b-medium", irreversible: "b-high" };
const SCOPE = { project: "Inside the project", outside_project: "Outside the project", network: "Leaves this machine", remote_repo: "Shared remote repository" };

function show(view) {
  for (const v of ["start", "session", "results"]) $(`#view-${v}`).classList.toggle("hidden", v !== view);
  if (view === "results") loadResults();
}
document.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));

async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
}

// ---------- start ----------
async function initStart() {
  const data = await api("/api/scenarios");
  const sel = $("#scenario-select");
  sel.innerHTML = data.scenarios.map((s) => `<option value="${esc(s.id)}">${esc(s.title)} (scripted)</option>`).join("") +
    (data.live_available ? `<option value="live">Live agent (real model, dry run)</option>` : "");
  $("#live-hint").textContent = data.live_available ? "" :
    "Live agent mode is off: set GROQ_API_KEY or OPENAI_API_KEY before starting the server to enable it.";
}

$("#start-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const out = await api("/api/sessions", { participant: f.get("participant"), condition: f.get("condition"), scenario: f.get("scenario") });
  session = out.session;
  $("#task-text").textContent = out.task;
  $("#cond-pill").textContent = out.condition === "card" ? "Consequence card" : "Raw command";
  $("#transcript").innerHTML = "";
  $("#report").classList.add("hidden");
  show("session");
  render(out);
});

// ---------- session ----------
function addEvent(ev) {
  const t = $("#transcript");
  const div = document.createElement("div");
  div.className = `ev ${ev.kind}`;
  if (ev.kind === "say") div.textContent = ev.text;
  else if (ev.kind === "ran") {
    const by = { you: "approved by you", contract: "ran without asking (read-only)", dont_ask_again: "auto-approved: you said don't ask again" }[ev.approved_by];
    div.innerHTML = `<span class="cmd">${esc(ev.action)}</span><span class="by ${ev.approved_by === "dont_ask_again" ? "auto" : ""}">${esc(by)}</span><span class="res">${esc(ev.result)}</span>`;
  } else if (ev.kind === "denied") div.textContent = ev.action;
  t.appendChild(div);
  t.scrollTop = t.scrollHeight;
}

function render(out) {
  out.events.forEach(addEvent);
  const p = $("#prompt");
  if (out.pending) {
    p.innerHTML = out.pending.condition === "card" ? cardHTML(out.pending) : rawHTML(out.pending);
    p.classList.remove("hidden");
    shownAt = performance.now();
    wirePrompt(out.pending);
    p.querySelector("button")?.focus({ preventScroll: true });
  } else p.classList.add("hidden");
  if (out.done) showReport();
}

function diffHTML(diff) {
  if (!diff) return "";
  return `<pre class="diff">${diff.split("\n").map((l) => `<span class="${l.startsWith("+") ? "add" : l.startsWith("-") ? "del" : ""}">${esc(l)}</span>`).join("\n")}</pre>`;
}

function rawHTML(a) {
  const kind = a.tool === "bash" ? "Bash command" : a.tool === "delete" ? "Delete file" : "Edit file";
  return `<div class="raw">
    <div class="title">${kind}</div>
    <div class="cmdline">${esc(a.tool === "bash" ? a.command : a.path)}</div>
    ${diffHTML(a.diff)}
    <div>Do you want to proceed?</div>
    <div class="opts" style="margin-top:8px">
      <button data-act="yes">1. Yes</button>
      <button data-act="always">2. Yes, and don't ask again for ${esc(a.class)} actions</button>
      <button data-act="no">3. No</button>
    </div></div>`;
}

function cardHTML(a) {
  const c = a.consequence;
  // Blanket approval is offered only for low-risk actions that can be undone:
  // an irreversible class should never be waved through (Lecture 12).
  const canAlways = c.reversibility === "undoable" && c.risk !== "high";
  return `<div class="cc">
    <div class="kicker">The agent wants to</div>
    <h2>${esc(c.effects[0])}</h2>
    <div class="badges">
      <span class="badge b-${esc(c.risk)}">Risk: ${esc(c.risk)}</span>
      <span class="badge ${REV_CLASS[c.reversibility]}">${REVERSIBILITY[c.reversibility]}</span>
      <span class="badge ${c.noticeable ? "b-low" : "b-medium"}">${c.noticeable ? "You would see the result" : "You would not see this happen"}</span>
      <span class="badge ${c.scope === "project" ? "b-low" : "b-high"}">${esc(SCOPE[c.scope] || c.scope)}</span>
    </div>
    <div><b>Changes:</b> ${esc(c.object)}</div>
    ${c.effects.length > 1 ? `<ul>${c.effects.slice(1).map((e) => `<li>${esc(e)}</li>`).join("")}</ul>` : ""}
    ${c.warnings.length ? `<ul class="warns">${c.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
    <div class="undo"><b>To undo:</b> ${esc(c.undo_hint)}</div>
    <div class="exact">Exact ${a.tool === "bash" ? "command" : "change"}<code>${esc(a.tool === "bash" ? a.command : a.label)}</code></div>
    ${diffHTML(a.diff)}
    <div class="actions">
      <button class="deny" data-act="no">Refuse</button>
      <button class="approve" data-act="yes">Approve</button>
      ${canAlways ? `<label><input type="checkbox" id="always"> Don't ask again for ${esc(c.action_class)}</label>` : ""}
    </div>
    <div class="source">Analysed by fixed rules in the checkpoint, not by the agent. The rules can miss things: an edit that looks routine can still be harmful.</div>
  </div>`;
}

function wirePrompt(a) {
  const p = $("#prompt");
  p.querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", () => {
    const act = b.dataset.act;
    const always = act === "always" || (act === "yes" && p.querySelector("#always")?.checked);
    decide(act !== "no", !!always);
  }));
  if (a.condition === "raw") {
    p.onkeydown = (e) => { const m = { 1: "yes", 2: "always", 3: "no" }[e.key]; if (m) p.querySelector(`[data-act=${m}]`).click(); };
  }
}

async function decide(approved, dontAsk) {
  const ms = Math.round(performance.now() - shownAt);
  $("#prompt").classList.add("hidden");
  const out = await api(`/api/sessions/${session}/decide`, { approved, dont_ask_again: dontAsk, ms });
  render(out);
}

async function showReport() {
  const r = await api(`/api/sessions/${session}/report`);
  const list = (xs, f) => xs.length ? `<ul>${xs.map(f).join("")}</ul>` : `<p class="none">None.</p>`;
  const el = $("#report");
  el.innerHTML = `<h2>What actually happened</h2>
    <p class="hint">Built from the action log and each action's return value, not from the agent's own summary.</p>
    <h3>The agent's summary (a claim)</h3><div class="claim">${esc(r.agent_claim || "(no summary)")}</div>
    <h3>Done (${r.done.length})</h3>${list(r.done, (d) => `<li><code>${esc(d.action)}</code>${d.approved_by === "dont_ask_again" ? " <b>(auto-approved)</b>" : ""}<br><span class="hint">${esc(d.result)}</span></li>`)}
    <h3>Refused by you (${r.refused.length})</h3>${list(r.refused, (a) => `<li><code>${esc(a)}</code></li>`)}
    <h3>Assumed on your behalf</h3>${list(r.assumed, (a) => `<li>${esc(a)}</li>`)}
    <h3>Cannot be fully undone</h3>${list(r.cannot_undo, (u) => `<li><code>${esc(u.action)}</code>: ${esc(u.why)}</li>`)}
    <p><button class="primary" data-view="start" id="again">Start another session</button></p>`;
  el.classList.remove("hidden");
  $("#again").addEventListener("click", () => show("start"));
}

// ---------- results ----------
const fmt = (v, pct) => v == null ? "–" : pct ? `${Math.round(v * 100)}%` : v;

async function loadResults() {
  const r = await api("/api/results");
  const conds = Object.entries(r.by_condition);
  if (!conds.length) { $("#results-body").innerHTML = `<p class="hint">No decisions logged yet.</p>`; return; }
  const row = (name, s) => `<tr><td>${esc(name)}</td><td>${s.decisions}</td><td>${fmt(s.approval_rate, 1)}</td><td>${fmt(s.hit_rate, 1)}</td><td>${s.misses}</td><td>${fmt(s.false_alarm_rate, 1)}</td><td>${fmt(s.d_prime)}</td><td>${fmt(s.criterion)}</td><td>${s.median_ms == null ? "–" : (s.median_ms / 1000).toFixed(1) + " s"}</td><td>${s.auto_approved}</td></tr>`;
  const label = { raw: "Raw command", card: "Consequence card" };
  let html = `<h2>By prompt design</h2><div class="tablewrap"><table><tr><th>Condition</th><th>Decisions</th><th>Approved</th><th>Hit rate</th><th>Misses</th><th>False alarms</th><th>d′</th><th>c</th><th>Median time</th><th>Auto-approved</th></tr>
    ${conds.map(([c, s]) => row(label[c] || c, s)).join("")}${row("All", r.overall)}</table></div>`;
  html += `<h2>Change with repeated use (blocks of 8 decisions per participant)</h2><div class="tablewrap"><table><tr><th>Participant · condition · block</th><th>Decisions</th><th>Approved</th><th>Hit rate</th><th>Misses</th><th>False alarms</th><th>d′</th><th>c</th><th>Median time</th><th>Auto</th></tr>
    ${Object.values(r.blocks).flat().map((b) => row(`${b.participant} · ${label[b.condition] || b.condition} · ${b.block}`, b)).join("")}</table></div>`;
  html += `<h2>Harmful actions that were approved</h2>` + (r.missed_actions.length
    ? `<ul>${r.missed_actions.map((m) => `<li><code>${esc(m.action)}</code> (${esc(m.seeded || "")}) by ${esc(m.participant)}, ${esc(label[m.condition])}${m.auto ? ", <b>auto-approved</b>" : ""}</li>`).join("")}</ul>`
    : `<p class="hint">None.</p>`);
  $("#results-body").innerHTML = html;
}

initStart();
