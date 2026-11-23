"""Turn the report into things the person can use right away (B3, B4, B7) and refresh the prompt-coach profile.

Usage: python finalize.py --out DIR [--no-profile]
Reads:  DIR/metrics.json, DIR/scores.json, DIR/narrative.json
Writes: DIR/targets.json                       next month's 3 targets (read by score.py next month)
        DIR/suggested/CLAUDE.md-snippet.md     rules the person keeps retyping, ready to paste into a project CLAUDE.md
        DIR/suggested/settings.allowlist.json  permissions.allow entries for commands they approve over and over
        DIR/suggested/commands/<name>.md       draft slash commands for repeated multi-step tasks
        DIR/coach-draft.json                   proposed coach focus, tips and templates + coach counts (uploaded for the lead)
        ~/.claude/prompt-coach/profile.json    only when team-config "approval_required" is false; otherwise the lead
                                               approves the draft (approve.py) and the coach loads it from Google Drive
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse, json, os, re
from datetime import date
from kpis import KPI_DEFS

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--no-profile", action="store_true")
args = ap.parse_args()
OUT = os.path.abspath(os.path.expanduser(args.out))


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        return json.load(fh)


m, s, nar = load("metrics.json"), load("scores.json"), load("narrative.json")
try:
    _local = json.load(open(os.environ.get("USAGE_REPORT_LOCAL") or os.path.join(os.path.expanduser("~"), ".claude", "usage-report.local.json"), encoding="utf-8"))
except Exception:
    _local = {}
lang = _local.get("language") or "hi"  # the person's coach language (coach_tips); the report itself is in report_language
SUG = os.path.join(OUT, "suggested")
os.makedirs(os.path.join(SUG, "commands"), exist_ok=True)

# B7 targets
targets = []
for t in nar.get("targets") or []:
    if t.get("metric") not in KPI_DEFS:
        raise SystemExit(f"narrative.targets: unknown metric '{t.get('metric')}'. Use one of {list(KPI_DEFS)}")
    targets.append({"metric": t["metric"], "label": KPI_DEFS[t["metric"]][0], "target": t["target"],
                    "baseline": (s.get("kpis") or {}).get(t["metric"]), "text": t.get("text", "")})
with open(os.path.join(OUT, "targets.json"), "w", encoding="utf-8") as fh:
    json.dump(targets, fh, indent=1, ensure_ascii=False)

# B3 CLAUDE.md snippet
lines = nar.get("claude_md_snippet") or []
if lines:
    with open(os.path.join(SUG, "CLAUDE.md-snippet.md"), "w", encoding="utf-8") as fh:
        fh.write("## Working rules (from my monthly Claude report)\n\n")
        fh.write("\n".join(f"- {x}" for x in lines) + "\n")

# B4 permissions allowlist
# Never suggest a bare interpreter (python, node, php ...) or tools that act outside the machine (gh, docker):
# those would let any script run without asking. Only "tool subcommand" pairs such as "npm run" or "php artisan".
BROAD = {"python", "python3", "py", "node", "php", "php.bat", "bun", "npx", "make", "go", "cargo", "dotnet", "pip"}
allow = [f"Bash({k} *)" for k, _ in m.get("allowlist_candidates") or []
         if " " in k and k.split()[0].lower() not in ("gh", "docker") and k.lower() not in ("git commit",)
         or (" " not in k and k.lower() not in BROAD and k.split("/")[-1] in ("pint", "phpstan", "pest", "phpunit", "eslint", "tsc"))]
with open(os.path.join(SUG, "settings.allowlist.json"), "w", encoding="utf-8") as fh:
    json.dump({"permissions": {"allow": allow}}, fh, indent=1)

# B4 draft slash commands
for c in nar.get("slash_commands") or []:
    name = re.sub(r"[^a-z0-9-]+", "-", str(c.get("name", "")).lower()).strip("-")
    if not name:
        continue
    with open(os.path.join(SUG, "commands", f"{name}.md"), "w", encoding="utf-8") as fh:
        fh.write(f"---\ndescription: {c.get('description', '').strip()}\nargument-hint: [details]\n---\n\n{c.get('body', '').strip()}\n")

# Prompt-coach profile
k = s.get("kpis") or {}
sig, pr = m.get("signals") or {}, m.get("practices") or {}
focus = []
if (sig.get("pct_done_check_openers") or 0) < 0.30:
    focus.append("done_check")
if (s.get("dimension_means") or {}).get("context", 5) < 3.2 or (sig.get("pct_context") or 0) < 0.15:
    focus.append("context")
if (sig.get("pct_bare_paste") or 0) > 0.03 or (sig.get("pct_image_only") or 0) > 0.03:
    focus.append("bare_paste")
if (m.get("pct_prompts_in_long_sessions") or 0) > 0.25 or (m.get("max_prompts_per_session") or 0) > 60:
    focus.append("long_sessions")
if pr.get("plan_on_big_rate") is not None and pr["plan_on_big_rate"] < 0.30:
    focus.append("plan_mode")

pdir = os.environ.get("PROMPT_COACH_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "prompt-coach")
ppath = os.path.join(pdir, "profile.json")
try:
    old = json.load(open(ppath, encoding="utf-8"))
except Exception:
    old = {}

# How often the coach stepped in during the report period (counts only; the log never holds prompt text).
coach_stats = {"prompts_checked": 0}
try:
    p0, p1 = m["period"][0], m["period"][1]
    for line in open(os.path.join(pdir, "log.jsonl"), encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if not (p0 <= str(r.get("ts", ""))[:10] <= p1):
            continue
        coach_stats["prompts_checked"] += 1
        coach_stats[r.get("action") or "none"] = coach_stats.get(r.get("action") or "none", 0) + 1
        for f in r.get("flags") or []:
            coach_stats["flag_" + f] = coach_stats.get("flag_" + f, 0) + 1
except Exception:
    pass

# The coach changes this report proposes. With approval_required (team-config), the team lead reviews and approves
# them first (approve.py), and the coach picks up the approved profile from Google Drive. Nothing changes locally.
draft = {
    "name": nar.get("person") or old.get("name"),
    "month": os.path.basename(OUT.rstrip("/\\")),
    "period": m["period"],
    "language": old.get("language") or lang,
    "focus": focus,
    "tips": nar.get("coach_tips") or old.get("tips") or [],
    "templates": [{"task": t.get("task"), "template": t.get("template")} for t in (nar.get("templates") or [])] or old.get("templates", []),
    "current": {k: old.get(k) for k in ("focus", "settings", "approved_rev", "approved_month")},
    "coach_stats": coach_stats,
    "created": date.today().isoformat(),
}
with open(os.path.join(OUT, "coach-draft.json"), "w", encoding="utf-8") as fh:
    json.dump(draft, fh, indent=1, ensure_ascii=False)

CFG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "team-config.json")
try:
    approval = json.load(open(CFG_PATH, encoding="utf-8")).get("approval_required", False)
except Exception:
    approval = False

profile_written = None
if not args.no_profile and not approval:
    # No team lead in the loop: update the coach directly.
    profile = {**old, "version": 1, "name": draft["name"], "language": draft["language"], "focus": focus,
               "tips": draft["tips"], "templates": draft["templates"], "settings": old.get("settings") or {},
               "updated": date.today().isoformat(), "source": f"usage-report {m['period'][0]}..{m['period'][1]}"}
    os.makedirs(pdir, exist_ok=True)
    with open(ppath, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=1, ensure_ascii=False)
    profile_written = ppath

print(json.dumps({"targets": len(targets), "claude_md_rules": len(lines), "allowlist": len(allow),
                  "slash_commands": len(nar.get("slash_commands") or []), "focus": focus,
                  "coach": ("waits for the team lead's approval (coach-draft.json)" if approval and not args.no_profile
                            else profile_written)}, ensure_ascii=False))
