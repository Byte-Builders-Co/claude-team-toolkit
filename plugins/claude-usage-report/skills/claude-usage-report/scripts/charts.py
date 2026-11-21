"""Weekly trend and hour-of-day charts. Usage: python charts.py --out DIR (reads DIR/metrics.json)."""
import argparse, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
OUT = os.path.abspath(os.path.expanduser(ap.parse_args().out))
m = json.load(open(os.path.join(OUT, "metrics.json"), encoding="utf-8"))
INK, MUTED, ACCENT = "#1f2933", "#7b8794", "#2f6fdb"


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=9)
    ax.grid(axis="y", color="#e4e7eb", linewidth=0.8)
    ax.set_axisbelow(True)


weeks = list(m["weekly"].items())
fig, ax = plt.subplots(figsize=(6.5, 2.6), dpi=200)
bars = ax.bar([w[5:].replace("-", "/") for w, _ in weeks], [v["prompts"] for _, v in weeks], color=ACCENT, width=0.6)
for b, (_, v) in zip(bars, weeks):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 2, f"{v['prompts']}\n{v['active_days']}d", ha="center", va="bottom", fontsize=8, color=INK)
style(ax)
ax.set_ylabel("Prompts", color=INK, fontsize=9)
ax.set_xlabel("Week starting (labels: prompts, active days)", color=MUTED, fontsize=8)
ax.set_ylim(0, max(1, max(v["prompts"] for _, v in weeks)) * 1.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "chart_weekly.png"))

hours = {int(k): v for k, v in m["hour_profile"].items()}
fig, ax = plt.subplots(figsize=(6.5, 2.2), dpi=200)
ax.bar(range(24), [hours.get(h, 0) for h in range(24)], color=ACCENT, width=0.7)
style(ax)
ax.set_xticks(range(0, 24, 2))
ax.set_ylabel("Prompts", color=INK, fontsize=9)
ax.set_xlabel(f"Hour of day ({m['timezone']})", color=MUTED, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "chart_hours.png"))
print("charts ok")
