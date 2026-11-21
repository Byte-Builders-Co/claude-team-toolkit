"""Prompt-quality score (PERSONAL.md 4c), Personal Leverage Score and plan-fit verdict (steps 3 and 5).

Usage: python score.py --out DIR [--plan Pro] [--price 20] [--currency USD]
Reads: DIR/metrics.json and DIR/judged_scores.csv (written by Claude after reading sample.txt).
judged_scores.csv columns: sample_id,date,project,goal,context,specificity,output,steering,technique,use_case,complexity
  (scores 1-5; leave steering empty when the session has no follow-ups; complexity = Light|Substantive|Advanced)
Writes: DIR/scores.json
"""
import argparse, csv, json, os, statistics
from datetime import date

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--plan", default="")
ap.add_argument("--price", type=float)
ap.add_argument("--currency", default="USD")
args = ap.parse_args()
OUT = os.path.abspath(os.path.expanduser(args.out))
DIMS = ["goal", "context", "specificity", "output", "steering", "technique"]

m = json.load(open(os.path.join(OUT, "metrics.json"), encoding="utf-8"))
rows = []
for r in csv.DictReader(open(os.path.join(OUT, "judged_scores.csv"), encoding="utf-8")):
    for d in DIMS:
        v = (r.get(d) or "").strip()
        r[d] = int(v) if v else None
        if r[d] is not None and not 1 <= r[d] <= 5:
            raise SystemExit(f"{r['sample_id']}: {d}={r[d]} is outside 1-5")
    rows.append(r)
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


def leverage(rate, ppwd, q, corr):
    parts = {
        "engagement": 30 * min(1, rate / 0.60),
        "depth": 15 * min(1, ppwd / 20),
        "breadth": 15 * min(1, m["breadth"] / min(6, m["detectable_capabilities"])),
        "quality": 30 * (q if q is not None else 0) / 100,
        "outcomes": 10 * statistics.mean([1 - corr, 1 - rej]),
    }
    if q is None:  # rescale remaining weights to 100
        parts.pop("quality")
        parts = {k: v * 100 / 70 for k, v in parts.items()}
    return {k: round(v, 1) for k, v in parts.items()}, round(sum(parts.values()), 1)


parts, total = leverage(m["active_day_rate"], m["prompts_per_working_day"], q_all, m["signals"]["correction_rate"])
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
    "n_judged": len(rows), "n_first": len(first), "n_second": len(second),
    "dimension_means": {k: round(v, 2) for k, v in dim_means.items()},
    "quality": q_all, "quality_first": q_first, "quality_second": q_second,
    "quality_by_complexity": {cx: quality([r for r in rows if r["complexity"] == cx])[1] for cx in mix_cx},
    "leverage_parts": parts, "leverage": total, "leverage_first": lev_first, "leverage_second": lev_second,
    "leverage_partial": q_all is None,
    "tier": tier, "champion_capped": total >= 80 and tier != "Champion",
    "use_case_mix": dict(sorted(mix_use.items(), key=lambda kv: -kv[1])), "complexity_mix": mix_cx,
    "plan": args.plan or None, "price_month": args.price, "currency": args.currency,
    "plan_verdict": verdict, "plan_verdict_proxy": limit_days == 0,
    "limit_days": limit_days, "limit_day_share": round(share, 3),
    "cost_per_active_day": round(args.price * m["calendar_days"] / 30 / m["active_days"], 2) if args.price and m["active_days"] else None,
}
json.dump(scores, open(os.path.join(OUT, "scores.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(scores, indent=1))
