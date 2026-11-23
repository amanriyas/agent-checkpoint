"""Rule-based consequence analyser.

Turns a proposed agent action into the facts a consequence card shows:
the object it changes, its side effects, whether it can be undone, whether
the person would notice, and a risk class.

Design note: this is deliberately NOT a language model. The card must not
be another fluent claim (Lecture 08: a model generates, it does not look
anything up). It is a fixed, inspectable rule table. When no rule matches,
the analyser says so instead of guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

PROJECT_ROOT = "~/projects/shop-api"


@dataclass
class Consequence:
    object: str                      # the thing that changes, named
    effects: list[str]               # side effects in plain words
    reversibility: str               # "undoable" | "hard_to_undo" | "irreversible"
    undo_hint: str                   # how to undo, or why you cannot
    noticeable: bool                 # would the person notice without being told?
    scope: str                       # "project" | "outside_project" | "network" | "remote_repo"
    risk: str                        # "low" | "medium" | "high"
    action_class: str                # used for "don't ask again for this class"
    matched_rule: str                # which rule fired, for the trace
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _cmd(action: dict) -> str:
    return (action.get("command") or "").strip()


def analyse(action: dict, known_packages: set[str] | None = None) -> Consequence:
    """Return the consequence of one proposed action.

    action: {"tool": "bash"|"edit"|"write"|"delete"|"read", "command"?, "path"?, "summary"?}
    known_packages: package names already in the project's requirements, used
    to flag installs of unfamiliar packages.
    """
    tool = action.get("tool", "bash")
    path = action.get("path", "")
    cmd = _cmd(action)
    known_packages = known_packages or set()

    if tool == "read":
        return Consequence(
            object=f"file {path}", effects=["Reads the file; changes nothing"],
            reversibility="undoable", undo_hint="Nothing to undo",
            noticeable=False, scope="project", risk="low",
            action_class="read", matched_rule="read-only")

    if tool in ("edit", "write"):
        warnings = []
        risk = "low"
        scope = "project"
        cls = "edit:source"
        if path.startswith(".github/workflows") or path.endswith(("ci.yml", ".gitlab-ci.yml")):
            risk = "high"
            cls = "edit:ci"
            warnings.append("Changes the CI pipeline: it decides which checks must pass before code ships")
            diff = action.get("diff", "")
            if "|| true" in diff or "continue-on-error: true" in diff:
                warnings.append("Makes a failing step count as passed")
        elif path.startswith(("~", "/")) or path.startswith(".."):
            risk = "high"
            scope = "outside_project"
            cls = "edit:outside"
            warnings.append("File is outside the project folder")
        elif path.endswith((".env", ".pem", "id_rsa", "credentials")):
            risk = "high"
            cls = "edit:secrets"
            warnings.append("File holds secrets")
        elif "test" in path:
            cls = "edit:tests"
            risk = "medium"
            diff = action.get("diff", "")
            if re.search(r"^-\s*(def test_|it\(|test\()", diff, re.M) or "skip" in diff:
                warnings.append("Removes or skips a test")
                risk = "high"
        return Consequence(
            object=f"file {path}",
            effects=[f"{'Overwrites' if tool == 'write' else 'Edits'} {path}"] + (
                [action["summary"]] if action.get("summary") else []),
            reversibility="undoable",
            undo_hint="Revert with git checkout -- " + path,
            noticeable=cls == "edit:source",
            scope=scope, risk=risk, action_class=cls,
            matched_rule=f"{tool}:{cls}", warnings=warnings)

    if tool == "delete":
        secret = path.endswith((".env", ".pem", "id_rsa", "credentials")) or "/.ssh" in path
        tracked = action.get("tracked", True)
        return Consequence(
            object=f"file {path}",
            effects=[f"Deletes {path}"],
            reversibility="undoable" if tracked else "irreversible",
            undo_hint=("Restore with git checkout -- " + path) if tracked
            else "Not tracked by git: no copy to restore from",
            noticeable=False, scope="outside_project" if path.startswith(("~", "/")) else "project",
            risk="high" if (secret or not tracked) else "medium",
            action_class="delete", matched_rule="delete",
            warnings=(["File holds secrets"] if secret else []) +
                     ([] if tracked else ["File is not under version control"]))

    # ---- bash commands ----
    rules: list[tuple[str, callable]] = [
        (r"^git\s+push\b.*(--force|-f\b)", _git_force_push),
        (r"^git\s+push\b", _git_push),
        (r"^git\s+reset\s+--hard", _git_reset_hard),
        (r"^git\s+(status|diff|log|show|branch)\b", _git_readonly),
        (r"^git\s+(add|commit|checkout -b|switch -c|stash)\b", _git_local),
        (r"^git\s+tag\b", _git_tag),
        (r"\b(curl|wget|http|nc)\b.*(-d|--data|-F|--upload-file|-T|@)", _network_upload),
        (r"^(curl|wget)\b", _network_fetch),
        (r"^rm\s+.*-[a-zA-Z]*r", _rm_recursive),
        (r"^rm\b", _rm_file),
        (r"^chmod\s+-R\s+777", _chmod_world),
        (r"^(pip|pip3|npm|yarn|pnpm)\s+(install|add|i)\b", _install),
        (r"^(pytest|npm test|npm run test|python -m pytest|make test)\b", _run_tests),
        (r"^(ls|cat|head|tail|grep|rg|find|pwd|echo)\b", _shell_readonly),
        (r"\b(psql|mysql|sqlite3)\b.*\b(DROP|TRUNCATE|DELETE)\b", _db_destructive),
        (r"^(python|python3|node)\s", _run_script),
    ]
    for pattern, fn in rules:
        if re.search(pattern, cmd, re.I):
            c = fn(cmd, known_packages)
            c.matched_rule = pattern
            return c

    return Consequence(
        object="unknown", effects=["No rule recognises this command; its effect is not known"],
        reversibility="hard_to_undo", undo_hint="Unknown: check the command yourself",
        noticeable=False, scope="project", risk="medium",
        action_class="bash:unknown", matched_rule="none",
        warnings=["Unrecognised command"])


# --- rule bodies -----------------------------------------------------------

def _branch(cmd: str) -> str:
    parts = [p for p in cmd.split() if not p.startswith("-")]
    return parts[-1] if len(parts) >= 4 else "current branch"


def _git_force_push(cmd, _):
    b = _branch(cmd)
    return Consequence(
        object=f"remote branch '{b}' on origin",
        effects=[f"Replaces the history of '{b}' on the shared remote",
                 "Teammates' commits not in your copy are discarded"],
        reversibility="irreversible",
        undo_hint="Only possible if someone still has the old commits locally",
        noticeable=False, scope="remote_repo", risk="high",
        action_class="git:push", matched_rule="",
        warnings=["Force push rewrites shared history"] +
                 (["Target is the main branch"] if b in ("main", "master") else []))


def _git_push(cmd, _):
    b = _branch(cmd)
    main = b in ("main", "master")
    return Consequence(
        object=f"remote branch '{b}' on origin",
        effects=[f"Publishes your local commits to '{b}' on the shared remote"],
        reversibility="hard_to_undo",
        undo_hint="Needs a revert commit; others may already have pulled",
        noticeable=True, scope="remote_repo", risk="high" if main else "medium",
        action_class="git:push", matched_rule="",
        warnings=["Target is the main branch"] if main else [])


def _git_reset_hard(cmd, _):
    return Consequence(
        object="working copy and recent commits",
        effects=["Discards uncommitted changes", "Moves the branch back; later commits leave the branch"],
        reversibility="hard_to_undo",
        undo_hint="Commits may be recoverable with git reflog; uncommitted work is lost",
        noticeable=False, scope="project", risk="high",
        action_class="git:reset", matched_rule="",
        warnings=["Uncommitted work cannot be recovered"])


def _git_readonly(cmd, _):
    return Consequence(object="git repository (read only)", effects=["Shows repository state; changes nothing"],
                       reversibility="undoable", undo_hint="Nothing to undo", noticeable=False,
                       scope="project", risk="low", action_class="git:read", matched_rule="")


def _git_local(cmd, _):
    return Consequence(object="local git repository", effects=["Records changes locally; nothing is shared yet"],
                       reversibility="undoable", undo_hint="git reset or git switch back", noticeable=True,
                       scope="project", risk="low", action_class="git:local", matched_rule="")


def _git_tag(cmd, _):
    return Consequence(object="local tag", effects=["Creates a release tag locally"],
                       reversibility="undoable", undo_hint="git tag -d <tag>", noticeable=True,
                       scope="project", risk="low", action_class="git:local", matched_rule="")


def _network_upload(cmd, _):
    host = re.search(r"https?://([^/\s]+)", cmd)
    host = host.group(1) if host else "an external host"
    sends_secret = bool(re.search(r"@?\.env|id_rsa|\.pem|credentials|token", cmd))
    return Consequence(
        object=f"data sent to {host}",
        effects=[f"Uploads local data to {host}"] + (["The data includes a secrets file"] if sends_secret else []),
        reversibility="irreversible", undo_hint="Data that has left the machine cannot be recalled",
        noticeable=False, scope="network", risk="high", action_class="net:upload", matched_rule="",
        warnings=["Sends data off this machine"] + (["Secrets leave the machine"] if sends_secret else []))


def _network_fetch(cmd, _):
    host = re.search(r"https?://([^/\s]+)", cmd)
    return Consequence(object=f"download from {host.group(1) if host else 'the network'}",
                       effects=["Downloads content from the internet"], reversibility="undoable",
                       undo_hint="Delete the downloaded file", noticeable=False, scope="network",
                       risk="medium", action_class="net:fetch", matched_rule="")


def _rm_recursive(cmd, _):
    target = cmd.split()[-1]
    outside = target.startswith(("~", "/", ".."))
    return Consequence(
        object=f"folder {target} and everything in it",
        effects=[f"Deletes {target} recursively"],
        reversibility="irreversible" if outside else "hard_to_undo",
        undo_hint="Untracked files are gone; tracked files can be restored from git",
        noticeable=False, scope="outside_project" if outside else "project", risk="high",
        action_class="fs:delete", matched_rule="",
        warnings=["Recursive delete"] + (["Target is outside the project"] if outside else []))


def _rm_file(cmd, _):
    target = cmd.split()[-1]
    secret = target.endswith((".env", ".pem", "id_rsa"))
    return Consequence(object=f"file {target}", effects=[f"Deletes {target}"],
                       reversibility="hard_to_undo", undo_hint="Restore from git if tracked; otherwise lost",
                       noticeable=False, scope="project", risk="high" if secret else "medium",
                       action_class="fs:delete", matched_rule="",
                       warnings=["File holds secrets"] if secret else [])


def _chmod_world(cmd, _):
    return Consequence(object="permissions of every file in the project",
                       effects=["Makes every file readable, writable and executable by any user"],
                       reversibility="hard_to_undo", undo_hint="Original permissions are not recorded",
                       noticeable=False, scope="project", risk="high", action_class="fs:perms",
                       matched_rule="", warnings=["World-writable files"])


def _install(cmd, known):
    pkgs = [p for p in cmd.split()[2:] if not p.startswith("-")]
    unknown = [p.split("==")[0].lower() for p in pkgs if p.split("==")[0].lower() not in known]
    return Consequence(
        object="package(s) " + ", ".join(pkgs) if pkgs else "project dependencies",
        effects=["Downloads and installs code that runs on this machine"],
        reversibility="undoable", undo_hint="Uninstall the package", noticeable=False,
        scope="network", risk="medium" if unknown else "low", action_class="pkg:install",
        matched_rule="",
        # The analyser can say a package is new to the project. It cannot tell a
        # typo-squat from a real new dependency: that judgement stays with the person.
        warnings=[f"Not in requirements: {', '.join(unknown)}"] if unknown else [])


def _run_tests(cmd, _):
    return Consequence(object="test suite", effects=["Runs the tests; changes nothing"],
                       reversibility="undoable", undo_hint="Nothing to undo", noticeable=True,
                       scope="project", risk="low", action_class="run:tests", matched_rule="")


def _shell_readonly(cmd, _):
    return Consequence(object="files (read only)", effects=["Lists or prints files; changes nothing"],
                       reversibility="undoable", undo_hint="Nothing to undo", noticeable=False,
                       scope="project", risk="low", action_class="shell:read", matched_rule="")


def _db_destructive(cmd, _):
    return Consequence(object="database tables", effects=["Deletes rows or tables in a database"],
                       reversibility="irreversible", undo_hint="Only from a backup, if one exists",
                       noticeable=False, scope="network", risk="high", action_class="db:destructive",
                       matched_rule="", warnings=["Destructive database command"])


def _run_script(cmd, _):
    parts = cmd.split()
    target = f"module {parts[2]}" if len(parts) > 2 and parts[1] == "-m" else f"script {parts[1]}"
    return Consequence(object=target, effects=["Runs a script; its effects depend on its code"],
                       reversibility="hard_to_undo", undo_hint="Depends on what the script does",
                       noticeable=False, scope="project", risk="medium", action_class="run:script",
                       matched_rule="")
