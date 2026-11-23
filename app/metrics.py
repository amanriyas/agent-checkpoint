"""Signal-detection scoring of approval decisions (Lecture 04).

Signal = a harmful action. The person "detects" it by denying it.

    hit               harmful action denied
    miss              harmful action approved (by hand or by "don't ask again")
    false alarm       safe action denied
    correct rejection safe action approved

d' (sensitivity) says how well the person tells harmful from safe actions.
c (criterion) says where they put the line: positive c = leaning towards
approving. A drop in hits with steady d' and rising c is a looser criterion;
a drop in d' is lost sensitivity. That is the A1 research question.
"""

from __future__ import annotations

from statistics import NormalDist, median

_z = NormalDist().inv_cdf


def _rate(k: int, n: int) -> float:
    # Log-linear correction (Hautus, 1995): keeps z finite at 0 and 1.
    return (k + 0.5) / (n + 1)


def score(decisions: list[dict]) -> dict:
    """decisions: dicts with 'harmful' (bool or None) and 'approved' (bool).

    Decisions with harmful=None (unlabelled live actions) are counted but
    left out of the detection scores.
    """
    labelled = [d for d in decisions if d.get("harmful") is not None]
    hits = sum(1 for d in labelled if d["harmful"] and not d["approved"])
    misses = sum(1 for d in labelled if d["harmful"] and d["approved"])
    fas = sum(1 for d in labelled if not d["harmful"] and not d["approved"])
    crs = sum(1 for d in labelled if not d["harmful"] and d["approved"])
    n_sig, n_noise = hits + misses, fas + crs

    out = {
        "decisions": len(decisions),
        "unlabelled": len(decisions) - len(labelled),
        "hits": hits, "misses": misses, "false_alarms": fas, "correct_rejections": crs,
        "approval_rate": round(sum(1 for d in decisions if d["approved"]) / len(decisions), 3) if decisions else None,
        "hit_rate": None, "false_alarm_rate": None, "d_prime": None, "criterion": None,
        "median_ms": None, "auto_approved": sum(1 for d in decisions if d.get("auto")),
    }
    times = [d["ms"] for d in decisions if d.get("ms") is not None and not d.get("auto")]
    if times:
        out["median_ms"] = int(median(times))
    if n_sig and n_noise:
        h, f = _rate(hits, n_sig), _rate(fas, n_noise)
        out["hit_rate"] = round(hits / n_sig, 3)
        out["false_alarm_rate"] = round(fas / n_noise, 3)
        out["d_prime"] = round(_z(h) - _z(f), 2)
        out["criterion"] = round(-(_z(h) + _z(f)) / 2, 2)
    return out


def by_block(decisions: list[dict], size: int = 8) -> list[dict]:
    """Score consecutive blocks of decisions, to show change with repeated use."""
    blocks = []
    for i in range(0, len(decisions), size):
        chunk = decisions[i:i + size]
        s = score(chunk)
        s["block"] = i // size + 1
        blocks.append(s)
    return blocks
