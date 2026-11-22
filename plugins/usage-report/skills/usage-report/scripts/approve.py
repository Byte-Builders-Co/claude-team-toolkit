"""Team lead: release approved coach profiles to each person's Google Drive folder.

Usage:
  python approve.py --root "G:/My Drive/Claude Reports" --month 2026-12 --names all            [--dry-run]
  python approve.py --root ... --month 2026-12 --names Avinash,Rushil
Reads:  <root>/_team/<month>/proposal.json   {Name: {"focus": [...], "tips": [...], "templates": [{"task","template"}],
                                                     "settings": {...}, "message": "one line for the person"}}
        (written by Claude from review_input.json, then changed as the lead asked)
Writes: <root>/<Name>/coach/profile.json      the profile the person's prompt coach loads at the next session start
        <root>/<Name>/coach/history/rev-N.json the previous approved profile
        <root>/_team/<month>/approved.json    who was released, with rev numbers
Each person's language and name stay on their own machine; the lead's focus, tips, templates and settings win.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse, json, os, re, shutil
from datetime import date, datetime, timedelta, timezone
from share import atomic_json, local_cfg

FOCUS = {"done_check", "context", "bare_paste", "long_sessions", "plan_mode"}
SETTINGS = {
    "enabled": lambda v: isinstance(v, bool),
    "block_mode": lambda v: v in ("block", "ask", "off"),
    "block_until": lambda v: v is None or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v))),
    "min_words": lambda v: isinstance(v, int) and 5 <= v <= 40,
    "long_session_prompts": lambda v: isinstance(v, int) and 10 <= v <= 100,
    "tip_every": lambda v: isinstance(v, int) and 1 <= v <= 10,
}


def read(p):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def validate(name, p):
    errs = []
    focus = p.get("focus") or []
    if not isinstance(focus, list) or any(f not in FOCUS for f in focus):
        errs.append(f"focus must be a list from {sorted(FOCUS)}")
    tips = p.get("tips") or []
    if not isinstance(tips, list) or not 1 <= len(tips) <= 6 or any(not isinstance(t, str) or not t.strip() or len(t) > 200 for t in tips):
        errs.append("tips: 1-6 non-empty strings, each up to 200 characters")
    tpl = p.get("templates") or []
    if not isinstance(tpl, list) or len(tpl) > 6 or any(not (isinstance(t, dict) and t.get("task") and t.get("template")) for t in tpl):
        errs.append("templates: up to 6 items of {task, template}")
    for k, v in (p.get("settings") or {}).items():
        if k not in SETTINGS:
            errs.append(f"settings.{k} is not a known setting ({', '.join(SETTINGS)})")
        elif not SETTINGS[k](v):
            errs.append(f"settings.{k}={v!r} is not allowed")
    if p.get("message") is not None and (not isinstance(p["message"], str) or len(p["message"]) > 300):
        errs.append("message: one line, up to 300 characters")
    return [f"{name}: {e}" for e in errs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--month", required=True)
    ap.add_argument("--names", required=True, help="all, or a comma list of names")
    ap.add_argument("--proposal")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    team_dir = os.path.join(root, "_team", a.month)
    proposal = read(a.proposal or os.path.join(team_dir, "proposal.json"))
    if not isinstance(proposal, dict) or not proposal:
        raise SystemExit(f"No proposal found at {a.proposal or os.path.join(team_dir, 'proposal.json')}")
    names = list(proposal) if a.names == "all" else [n.strip() for n in a.names.split(",") if n.strip()]
    unknown = [n for n in names if n not in proposal]
    if unknown:
        raise SystemExit(f"Not in proposal.json: {', '.join(unknown)}")
    no_folder = [n for n in names if not os.path.isdir(os.path.join(root, n))]
    if no_folder:
        raise SystemExit(f"No Drive folder for: {', '.join(no_folder)} (expected {root}/<Name>/)")
    errs = [e for n in names for e in validate(n, proposal[n])]
    if errs:
        raise SystemExit("Fix proposal.json:\n  " + "\n  ".join(errs))

    lead = local_cfg().get("name") or "team lead"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    released = {}
    for n in names:
        p = proposal[n]
        cdir = os.path.join(root, n, "coach")
        prev = read(os.path.join(cdir, "profile.json")) or {}
        settings = {**(prev.get("settings") or {}), **(p.get("settings") or {})}
        if settings.get("block_mode") == "block" and not settings.get("block_until"):
            settings["block_until"] = (date.today() + timedelta(days=21)).isoformat()
        prof = {"name": n, "focus": p.get("focus") or [], "tips": p.get("tips") or [],
                "templates": [{"task": t["task"], "template": t["template"]} for t in p.get("templates") or []],
                "settings": settings, "message": p.get("message"),
                "rev": int(prev.get("rev") or 0) + 1, "approved_at": now, "approved_month": a.month, "approved_by": lead}
        changes = {k: [prev.get(k), prof[k]] for k in ("focus", "settings") if prev.get(k) != prof[k]}
        if prev.get("tips") != prof["tips"]:
            changes["tips"] = f"{len(prev.get('tips') or [])} -> {len(prof['tips'])} tips"
        if prev.get("templates") != prof["templates"]:
            changes["templates"] = f"{len(prev.get('templates') or [])} -> {len(prof['templates'])} templates"
        released[n] = {"rev": prof["rev"], "changes": changes}
        if a.dry_run:
            continue
        if prev:
            os.makedirs(os.path.join(cdir, "history"), exist_ok=True)
            shutil.copyfile(os.path.join(cdir, "profile.json"), os.path.join(cdir, "history", f"rev-{prev.get('rev') or 0}.json"))
        atomic_json(os.path.join(cdir, "profile.json"), prof)
    if not a.dry_run:
        log = read(os.path.join(team_dir, "approved.json")) or {}
        log.update({n: {"rev": r["rev"], "approved_at": now} for n, r in released.items()})
        atomic_json(os.path.join(team_dir, "approved.json"), log)
    print(json.dumps({"dry_run": a.dry_run, "released": released}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
