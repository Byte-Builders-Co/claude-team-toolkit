"""Shared KPI definitions for the monthly report, progress tracking and the team dashboard.

kpis(metrics, scores) -> {key: value or None}. None means "not measured" (for example v1 reports), never 0.
"""

# key: (label, better direction, unit)
KPI_DEFS = {
    "quality":              ("Prompt quality", "up", "/100"),
    "quality_quick":        ("Quality on quick tasks", "up", "/100"),
    "output_dim":           ("Output specification", "up", "/5"),
    "pct_done_check":       ("Prompts that say what 'done' means", "up", "%"),
    "pct_bare_paste":       ("Pastes with no instruction", "down", "%"),
    "plan_on_big_rate":     ("Plan mode on big tasks", "up", "%"),
    "verify_rate":          ("Sessions where Claude ran tests/lint", "up", "%"),
    "avg_prompts_per_session": ("Prompts per session", "down", ""),
    "pct_prompts_in_long_sessions": ("Prompts in 30+ prompt sessions", "down", "%"),
    "correction_rate":      ("Re-asks / corrections", "down", "%"),
    "limit_days":           ("Usage-limit days", "down", ""),
    "data_flags":           ("Sensitive-data flags", "down", ""),
    "active_day_rate":      ("Active working days", "up", "%"),
    "leverage":             ("Leverage Score", "up", "/100"),
}

USE_CASES = ["Feature build", "Bug fix / debugging", "UI / styling", "Tests & QA", "Refactor / cleanup",
             "DevOps / config", "Investigation / review", "Docs / planning / research", "Git & release", "Other"]
COMPLEXITY = ["Light", "Substantive", "Advanced"]
# v1 reports used other labels; map them so old and new months line up.
COMPLEXITY_MAP = {"low": "Light", "light": "Light", "medium": "Substantive", "substantive": "Substantive",
                  "high": "Advanced", "advanced": "Advanced"}


def _get(d, *path):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d


def kpis(m, s):
    v2 = (m.get("method_version") or 1) >= 2
    qcx = {COMPLEXITY_MAP.get(str(k).lower(), k): v for k, v in (s.get("quality_by_complexity") or {}).items()}
    out = {
        "quality": s.get("quality"),
        "quality_quick": qcx.get("Light"),
        "output_dim": _get(s, "dimension_means", "output"),
        "pct_done_check": _get(m, "signals", "pct_done_check") if v2 else None,
        "pct_bare_paste": _get(m, "signals", "pct_bare_paste") if v2 else None,
        "plan_on_big_rate": _get(m, "practices", "plan_on_big_rate") if v2 else None,
        "verify_rate": _get(m, "practices", "verify_rate") if v2 else None,
        "avg_prompts_per_session": m.get("avg_prompts_per_session") if v2 else None,
        "pct_prompts_in_long_sessions": m.get("pct_prompts_in_long_sessions") if v2 else None,
        "correction_rate": _get(m, "signals", "correction_rate"),
        "limit_days": len(m.get("limit_hit_days") or []),
        "data_flags": sum((m.get("data_handling") or {}).values()),
        "active_day_rate": m.get("active_day_rate"),
        "leverage": s.get("leverage") if (s.get("method_version") or 1) >= 2 else None,
    }
    if not v2:
        # v1 counted /clear as prompts and used Mon-Fri with no holidays: rebuild what can be rebuilt,
        # and leave the rest as "not measured".
        out["active_day_rate"] = None
        clears = dict(m.get("skills_used") or []).get("/clear", 0)
        if m.get("sessions"):
            out["avg_prompts_per_session"] = round((m.get("prompts", 0) - clears) / m["sessions"], 2)
    return out
