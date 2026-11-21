"""Combine the team's monthly reports into one history file and a summary table (B9).

Usage: python team_summary.py --month-dir "Reports/2026-12" --label 2026-12 --history "Reports/history.json"
Reads:  <month-dir>/<Name>/metrics.json and scores.json  (only these; never raw prompts)
Writes: history.json (all months; this month added or replaced), <month-dir>/team_summary.md
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

ap = argparse.ArgumentParser()
ap.add_argument("--month-dir", required=True)
ap.add_argument("--label", required=True, help="YYYY-MM")
ap.add_argument("--history", required=True)
args = ap.parse_args()

members, periods = {}, []
for name in sorted(os.listdir(args.month_dir)):
    d = os.path.join(args.month_dir, name)
    mp, sp = os.path.join(d, "metrics.json"), os.path.join(d, "scores.json")
    if not (os.path.isdir(d) and os.path.exists(mp) and os.path.exists(sp)):
        continue
    m, s = json.load(open(mp, encoding="utf-8")), json.load(open(sp, encoding="utf-8"))
    members[name] = {"method_version": m.get("method_version") or 1, "period": m.get("period"),
                     "kpis": kpis(m, s), "plan_verdict": s.get("plan_verdict"), "tier": s.get("tier")}
    periods.append(tuple(m.get("period") or ()))
if not members:
    raise SystemExit(f"No <Name>/metrics.json + scores.json found under {args.month_dir}")

team = {}
for k in KPI_DEFS:
    vals = [v["kpis"][k] for v in members.values() if v["kpis"].get(k) is not None]
    team[k] = round(statistics.median(vals), 3) if vals else None

hist = {"kpis": {}, "months": {}}
if os.path.exists(args.history):
    hist = json.load(open(args.history, encoding="utf-8"))
hist["kpis"] = {k: list(v) for k, v in KPI_DEFS.items()}
hist["months"][args.label] = {"period": [min(p[0] for p in periods if p), max(p[1] for p in periods if p)],
                              "members": members, "team": team}
hist["months"] = dict(sorted(hist["months"].items()))
json.dump(hist, open(args.history, "w", encoding="utf-8"), indent=1)


def fmt(k, v):
    if v is None:
        return "–"
    return f"{v * 100:.0f}%" if KPI_DEFS[k][2] == "%" else f"{v:g}"


names = list(members)
lines = [f"# Team summary {args.label}", "", "| KPI | " + " | ".join(names) + " | Team median |",
         "|---|" + "---|" * (len(names) + 1)]
for k, (label, better, unit) in KPI_DEFS.items():
    lines.append(f"| {label} ({'↑' if better == 'up' else '↓'} better) | " + " | ".join(fmt(k, members[n]["kpis"][k]) for n in names) + f" | {fmt(k, team[k])} |")
lines += ["", "– = not measured (for example a v1 report). Method versions: " + ", ".join(f"{n} v{members[n]['method_version']}" for n in names)]
open(os.path.join(args.month_dir, "team_summary.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"\nhistory -> {args.history} ({len(hist['months'])} months)")
