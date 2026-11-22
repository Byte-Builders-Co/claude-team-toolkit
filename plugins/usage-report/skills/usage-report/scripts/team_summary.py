"""Combine the team's monthly reports into one history file, a summary table and the lead's review input (B9).

Google Drive layout (recommended):
  python team_summary.py --root "G:/My Drive/Claude Reports" --label 2026-12
  Reads  <root>/<Name>/<YYYY-MM>/metrics.json, scores.json, coach-draft.json and <root>/<Name>/coach/profile.json
  Writes <root>/_team/history.json, <root>/_team/kpi_history.csv,
         <root>/_team/<YYYY-MM>/team_summary.md and review_input.json
Old layout:
  python team_summary.py --month-dir "Reports/2026-12" --label 2026-12 --history "Reports/history.json"
  Reads  <month-dir>/<Name>/metrics.json and scores.json
Only these files are read; never raw prompts.
history.json: {"kpis": {key: [label, better, unit]},
               "months": {"YYYY-MM": {"period": [start, end], "members": {Name: {"method_version": n, "kpis": {...},
                          "plan_verdict": str, "tier": str}}, "team": {key: median or null}}}}
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse, json, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kpis import kpis, KPI_DEFS

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--root", help="Google Drive team folder: <root>/<Name>/<YYYY-MM>/")
ap.add_argument("--month-dir", help="old layout: <month-dir>/<Name>/")
ap.add_argument("--label", required=True, help="YYYY-MM")
ap.add_argument("--history")
ap.add_argument("--config", default=os.path.join(SKILL_DIR, "team-config.json"))
args = ap.parse_args()
if not (args.root or args.month_dir):
    ap.error("give --root (Google Drive layout) or --month-dir (old layout)")
CFG = json.load(open(args.config, encoding="utf-8")) if os.path.exists(args.config) else {}


def read(p):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None  # missing, or still syncing from Drive


if args.root:
    ROOT = os.path.abspath(args.root)
    TEAM_DIR = os.path.join(ROOT, "_team", args.label)
    HISTORY = args.history or os.path.join(ROOT, "_team", "history.json")
    dirs = {n: os.path.join(ROOT, n, args.label) for n in sorted(os.listdir(ROOT))
            if not n.startswith(("_", ".")) and os.path.isdir(os.path.join(ROOT, n))}
else:
    ROOT, TEAM_DIR = None, args.month_dir
    HISTORY = args.history or os.path.join(os.path.dirname(os.path.abspath(args.month_dir)), "history.json")
    dirs = {n: os.path.join(args.month_dir, n) for n in sorted(os.listdir(args.month_dir))
            if os.path.isdir(os.path.join(args.month_dir, n))}
os.makedirs(TEAM_DIR, exist_ok=True)

members, periods, review = {}, [], {}
for name, d in dirs.items():
    m, s = read(os.path.join(d, "metrics.json")), read(os.path.join(d, "scores.json"))
    if not (m and s):
        continue
    members[name] = {"method_version": m.get("method_version") or 1, "period": m.get("period"),
                     "kpis": kpis(m, s), "plan_verdict": s.get("plan_verdict"), "tier": s.get("tier")}
    periods.append(tuple(m.get("period") or ()))
    if ROOT:
        review[name] = {"kpis": members[name]["kpis"], "tier": s.get("tier"), "leverage": s.get("leverage"),
                        "quality": s.get("quality"), "progress": s.get("progress"),
                        "draft": read(os.path.join(d, "coach-draft.json")),
                        "approved": read(os.path.join(ROOT, name, "coach", "profile.json"))}
expected = CFG.get("members") or []
missing = [n for n in expected if n not in members]
if not members:
    raise SystemExit(f"No reports found for {args.label}. Missing: {', '.join(missing) or 'everyone'}")

team = {}
for k in KPI_DEFS:
    vals = [v["kpis"][k] for v in members.values() if v["kpis"].get(k) is not None]
    team[k] = round(statistics.median(vals), 3) if vals else None

hist = {"kpis": {}, "months": {}}
if os.path.exists(HISTORY):
    hist = json.load(open(HISTORY, encoding="utf-8"))
hist["kpis"] = {k: list(v) for k, v in KPI_DEFS.items()}
hist["months"][args.label] = {"period": [min(p[0] for p in periods if p), max(p[1] for p in periods if p)],
                              "members": members, "team": team}
hist["months"] = dict(sorted(hist["months"].items()))
json.dump(hist, open(HISTORY, "w", encoding="utf-8"), indent=1)

# Flat CSV of every month for the team dashboard: one row per month x member x KPI ("" = not measured).
import csv
csv_path = os.path.join(os.path.dirname(os.path.abspath(HISTORY)), "kpi_history.csv")
with open(csv_path, "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["month", "member", "kpi", "label", "better", "unit", "value", "method_version"])
    for label_m, mo in hist["months"].items():
        for who, info in list(mo["members"].items()) + [("Team median", {"kpis": mo["team"], "method_version": ""})]:
            for k, (label, better, unit) in KPI_DEFS.items():
                v = info["kpis"].get(k)
                w.writerow([label_m, who, k, label, better, unit, "" if v is None else v, info.get("method_version", "")])


def fmt(k, v):
    if v is None:
        return "–"
    return f"{v * 100:.0f}%" if KPI_DEFS[k][2] == "%" else f"{v:g}"


names = list(members)
lines = [f"# Team summary {args.label}", "", "| KPI | " + " | ".join(names) + " | Team median |",
         "|---|" + "---|" * (len(names) + 1)]
for k, (label, better, unit) in KPI_DEFS.items():
    lines.append(f"| {label} ({'↑' if better == 'up' else '↓'} better) | " + " | ".join(fmt(k, members[n]["kpis"][k]) for n in names) + f" | {fmt(k, team[k])} |")
lines += ([""] + [f"Not submitted yet: {', '.join(missing)}"] if missing else []) + ["", "– = not measured (for example a v1 report). Method versions: " + ", ".join(f"{n} v{members[n]['method_version']}" for n in names)]
open(os.path.join(TEAM_DIR, "team_summary.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
if ROOT:
    with open(os.path.join(TEAM_DIR, "review_input.json"), "w", encoding="utf-8") as fh:
        json.dump({"month": args.label, "missing": missing, "members": review}, fh, indent=1, ensure_ascii=False)
print(f"\nhistory -> {HISTORY} ({len(hist['months'])} months)")
print(f"csv     -> {csv_path}")
print(f"review  -> {os.path.join(TEAM_DIR, 'review_input.json') if ROOT else 'n/a (old layout)'}")
print("MISSING: " + (", ".join(missing) if missing else "none"))
