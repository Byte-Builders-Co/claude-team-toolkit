"""Prompt-quality score (PERSONAL.md 4c), Personal Leverage Score v2, plan-fit verdict and progress vs last month.

Usage: python score.py --out DIR [--plan Pro] [--price 20] [--currency USD] [--prev PREV_DIR | --no-prev]
Reads: DIR/metrics.json and DIR/judged_scores.csv (written by Claude after reading sample.txt);
       team-config.json for plan defaults; the previous month's metrics.json / scores.json / targets.json.
judged_scores.csv columns: sample_id,date,project,goal,context,specificity,output,steering,technique,use_case,complexity
  (scores 1-5; leave steering empty when the session has no follow-ups;
   use_case and complexity must use the fixed lists in kpis.py)
Writes: DIR/scores.json
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse, csv, json, os, statistics, glob
from datetime import date
from kpis import kpis, KPI_DEFS, USE_CASES, COMPLEXITY

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--plan")
ap.add_argument("--price", type=float)
ap.add_argument("--currency")
ap.add_argument("--config", default=os.path.join(SKILL_DIR, "team-config.json"))
ap.add_argument("--prev", help="folder of the previous month's report (default: newest older folder next to DIR)")
ap.add_argument("--no-prev", action="store_true")
args = ap.parse_args()
CFG = json.load(open(args.config, encoding="utf-8")) if args.config and os.path.exists(args.config) else {}
PLAN = args.plan or CFG.get("plan") or ""
PRICE = args.price if args.price is not None else CFG.get("price_month")
CURRENCY = args.currency or CFG.get("currency") or "USD"
OUT = os.path.abspath(os.path.expanduser(args.out))
DIMS = ["goal", "context", "specificity", "output", "steering", "technique"]

m = json.load(open(os.path.join(OUT, "metrics.json"), encoding="utf-8"))
rows, problems = [], []
for r in csv.DictReader(open(os.path.join(OUT, "judged_scores.csv"), encoding="utf-8")):
    for d in DIMS:
        v = (r.get(d) or "").strip()
        r[d] = int(v) if v else None
        if r[d] is not None and not 1 <= r[d] <= 5:
            problems.append(f"{r['sample_id']}: {d}={r[d]} is outside 1-5")
    r["use_case"] = (r.get("use_case") or "").strip()
    r["complexity"] = (r.get("complexity") or "").strip()
    if r["use_case"] not in USE_CASES:
        problems.append(f"{r['sample_id']}: use_case '{r['use_case']}' is not one of {USE_CASES}")
    if r["complexity"] not in COMPLEXITY:
        problems.append(f"{r['sample_id']}: complexity '{r['complexity']}' is not one of {COMPLEXITY}")
    rows.append(r)
if problems:
    raise SystemExit("Fix judged_scores.csv:\n  " + "\n  ".join(problems))
if not rows:
    raise SystemExit("judged_scores.csv is empty")


def quality(rs):
    if not rs:
        return {}, None
    means = {}
    for d in DIMS:
        vals = [r[d] for r in rs if r[d] is not None]
        if vals:
            means[d] = statistics.mean(vals)
    return means, round((statistics.mean(means.values()) - 1) / 4 * 100, 1)


split = date.fromisoformat(m["halves"]["split_after"])
dim_means, q_all = quality(rows)
first = [r for r in rows if date.fromisoformat(r["date"]) <= split]
second = [r for r in rows if date.fromisoformat(r["date"]) > split]
q_first, q_second = quality(first)[1], quality(second)[1]
rej = m.get("edit_rejection_rate") or 0
sig, pr = m["signals"], m.get("practices") or {}


def practices_score():
    """Share of good habits, each scaled to a target. Missing ones (e.g. no big sessions) are left out."""
    parts = {
        "done_check": min(1, (sig.get("pct_done_check_openers") or 0) / 0.40),
        "verify": None if pr.get("verify_rate") is None else min(1, pr["verify_rate"] / 0.60),
        "plan_on_big": None if pr.get("plan_on_big_rate") is None else min(1, pr["plan_on_big_rate"] / 0.50),
        "session_hygiene": 1 - min(1, (m.get("pct_prompts_in_long_sessions") or 0) / 0.50),
    }
    vals = [v for v in parts.values() if v is not None]
    return {k: (None if v is None else round(v, 2)) for k, v in parts.items()}, (statistics.mean(vals) if vals else 0)


prac_parts, prac = practices_score()


def leverage(rate, ppwd, q, corr):
    parts = {
        "engagement": 20 * min(1, rate / 0.70),
        "depth": 10 * min(1, ppwd / 20),
        "breadth": 10 * min(1, m["breadth"] / min(6, m["detectable_capabilities"])),
        "quality": 30 * (q if q is not None else 0) / 100,
        "practices": 20 * prac,
        "outcomes": 10 * statistics.mean([1 - corr, 1 - rej]),
    }
    if q is None:  # rescale remaining weights to 100
        parts.pop("quality")
        parts = {k: v * 100 / 70 for k, v in parts.items()}
    return {k: round(v, 1) for k, v in parts.items()}, round(sum(parts.values()), 1)


parts, total = leverage(m["active_day_rate"], m["prompts_per_working_day"], q_all, sig["correction_rate"])
h1, h2 = m["halves"]["first"], m["halves"]["second"]
lev_first = leverage(h1["active_day_rate"], h1["prompts_per_working_day"], q_first, h1["correction_rate"])[1]
lev_second = leverage(h2["active_day_rate"], h2["prompts_per_working_day"], q_second, h2["correction_rate"])[1]
tier = ("Champion" if total >= 80 and (q_all or 0) >= 60 else "Proficient" if total >= 60 else
        "Developing" if total >= 40 else "Light user" if total >= 20 else "Barely used")
mix_use, mix_cx = {}, {}
for r in rows:
    mix_use[r["use_case"]] = mix_use.get(r["use_case"], 0) + 1
    mix_cx[r["complexity"]] = mix_cx.get(r["complexity"], 0) + 1
limit_days = len(m["limit_hit_days"])
share = limit_days / m["active_days"] if m["active_days"] else 0
verdict = ("Constrained" if limit_days >= 3 or share > 0.10 else
           "Well matched" if m["active_day_rate"] >= 0.40 else "Under-used")
scores = {
    "method_version": 2,
    "n_judged": len(rows), "n_first": len(first), "n_second": len(second),
    "dimension_means": {k: round(v, 2) for k, v in dim_means.items()},
    "quality": q_all, "quality_first": q_first, "quality_second": q_second,
    "quality_by_complexity": {cx: quality([r for r in rows if r["complexity"] == cx])[1] for cx in COMPLEXITY if cx in mix_cx},
    "quality_by_use_case": {u: quality([r for r in rows if r["use_case"] == u])[1] for u in mix_use},
    "practices_parts": prac_parts,
    "leverage_parts": parts, "leverage": total, "leverage_first": lev_first, "leverage_second": lev_second,
    "leverage_partial": q_all is None,
    "tier": tier, "champion_capped": total >= 80 and tier != "Champion",
    "use_case_mix": dict(sorted(mix_use.items(), key=lambda kv: -kv[1])),
    "complexity_mix": {cx: mix_cx[cx] for cx in COMPLEXITY if cx in mix_cx},
    "plan": PLAN or None, "price_month": PRICE, "currency": CURRENCY,
    "plan_verdict": verdict, "plan_verdict_proxy": limit_days == 0,
    "limit_days": limit_days, "limit_day_share": round(share, 3),
    "cost_per_active_day": round(PRICE * m["calendar_days"] / 30 / m["active_days"], 2) if PRICE and m["active_days"] else None,
}
scores["kpis"] = kpis(m, scores)

# ---- B7: progress vs the previous report and last month's targets ------------------------
prev_dir = None
if not args.no_prev:
    if args.prev:
        prev_dir = os.path.abspath(os.path.expanduser(args.prev))
    else:
        cands = []
        for f in glob.glob(os.path.join(os.path.dirname(OUT), "*", "scores.json")):
            d = os.path.dirname(f)
            if os.path.abspath(d) == OUT:
                continue
            try:
                pm = json.load(open(os.path.join(d, "metrics.json"), encoding="utf-8"))
                # an earlier report = one that started earlier (v1 reports were rolling 30-day windows that overlap)
                if pm["period"][0] < m["period"][0]:
                    cands.append((pm["period"][0], d))
            except Exception:
                continue
        prev_dir = max(cands)[1] if cands else None
if prev_dir and os.path.exists(os.path.join(prev_dir, "scores.json")):
    pm = json.load(open(os.path.join(prev_dir, "metrics.json"), encoding="utf-8"))
    ps = json.load(open(os.path.join(prev_dir, "scores.json"), encoding="utf-8"))
    pk = kpis(pm, ps)
    progress = {}
    for k, (label, better, unit) in KPI_DEFS.items():
        a, b = pk.get(k), scores["kpis"].get(k)
        if a is None or b is None:
            progress[k] = {"label": label, "prev": a, "now": b, "change": None}
            continue
        improved = (b > a) if better == "up" else (b < a)
        progress[k] = {"label": label, "prev": a, "now": b, "change": round(b - a, 3),
                       "improved": improved if a != b else None}
    targets_out = []
    tpath = os.path.join(prev_dir, "targets.json")
    if os.path.exists(tpath):
        for t in json.load(open(tpath, encoding="utf-8")):
            now = scores["kpis"].get(t.get("metric"))
            better = KPI_DEFS.get(t.get("metric"), ("", "up", ""))[1]
            met = None if now is None else (now >= t["target"] if better == "up" else now <= t["target"])
            targets_out.append({**t, "now": now, "met": met})
    scores["progress"] = {"prev_period": pm["period"], "prev_method_version": pm.get("method_version") or 1,
                          "kpis": progress, "targets": targets_out}
json.dump(scores, open(os.path.join(OUT, "scores.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps({k: scores[k] for k in ("quality", "leverage", "tier", "plan_verdict", "kpis")}, indent=1))
print("progress vs " + (prev_dir or "none (first report)"))
