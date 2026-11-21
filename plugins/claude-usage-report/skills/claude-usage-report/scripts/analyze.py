"""Personal Claude Code usage metrics (PERSONAL.md steps 1-4a) and the judged sample.

Usage: python analyze.py --out DIR [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--tz Area/City]
Defaults: the 30 days ending yesterday, in the system time zone.
Writes: metrics.json, prompts.csv (raw prompt text, keep private), sample.txt, sample_index.csv.
"""
import argparse, json, glob, os, re, csv, collections, statistics, random
from datetime import datetime, date, timedelta

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--start")
ap.add_argument("--end")
ap.add_argument("--tz")
ap.add_argument("--sample", type=int, default=45)
args = ap.parse_args()

OUT = os.path.abspath(os.path.expanduser(args.out))
os.makedirs(OUT, exist_ok=True)
TZ = None
if args.tz:
    try:
        from zoneinfo import ZoneInfo
        TZ = ZoneInfo(args.tz)
    except Exception:
        print(f"WARNING: time zone {args.tz} unavailable (pip install tzdata); using system offset")
TZ = TZ or datetime.now().astimezone().tzinfo
TZ_NAME = args.tz or str(datetime.now().astimezone().tzname())
END = date.fromisoformat(args.end) if args.end else datetime.now(TZ).date() - timedelta(1)
START = date.fromisoformat(args.start) if args.start else END - timedelta(29)
MID = START + (END - START) / 2
ROOT = os.path.expanduser("~/.claude/projects")

SKIP_TAGS = ("task-notification", "bash-input", "bash-stdout", "bash-stderr", "local-command-stdout",
             "local-command-caveat", "system-reminder", "artifact-content-authored-by-others")
FORMAT_RE = re.compile(r"\b(table|bullet|list|json|csv|markdown|steps?|checklist|summar(y|ise|ize)|in \d+ words|one line|short|concise|diff|pr description|commit message|format)\b", re.I)
CONTEXT_RE = re.compile(r"\b(because|so that|for (our|my|the) |goal|context|background|currently|we (use|have|are)|I (want|need|am trying)|the reason|users? (can|should)|client|production|prod|staging)\b", re.I)
CORRECT_RE = re.compile(r"^\s*(no\b|nope|wrong|that'?s (not|wrong)|not what i|try again|still (not|getting|failing|same)|doesn'?t work|didn'?t work|it'?s not working|again\b|same (error|issue)|you (missed|forgot|didn'?t))", re.I)
SECRET_RES = {
    "api_key_or_token": re.compile(r"(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})"),
    "password": re.compile(r"(password|passwd|pwd|DB_PASSWORD|secret)\s*[:=]\s*\S{4,}", re.I),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def luhn(num: str) -> bool:
    d = [int(c) for c in num if c.isdigit()]
    s = 0
    for i, x in enumerate(reversed(d)):
        if i % 2:
            x = x * 2 - 9 if x > 4 else x * 2
        s += x
    return len(d) >= 13 and s % 10 == 0


def text_of(c) -> str:
    if isinstance(c, str):
        return c
    return "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")


def local(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(TZ)


def in_period(d: date) -> bool:
    return START <= d <= END


files = glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True)
prompts, tool_uses, usage_by_msg = [], collections.Counter(), {}
edit_ids, rejected_edits, files_edited = set(), set(), set()
commits, prs, limit_days, limit_events, warn_days = 0, set(), set(), 0, set()
lines_by_session, hook_sessions, plan_mode_sessions = {}, set(), set()
skills_used, mcp_servers, subagent_calls, web_calls, images = collections.Counter(), collections.Counter(), 0, 0, 0
denials = collections.Counter()
earliest_event = None

for f in files:
    with open(f, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except Exception:
                continue
            t, ts, sid = e.get("type"), e.get("timestamp"), e.get("sessionId")
            d = local(ts).date() if ts else None
            if d and (earliest_event is None or d < earliest_event):
                earliest_event = d
            if t == "pr-link" and d and in_period(d):
                prs.add(e.get("prUrl"))
            if t == "cost-state":
                lines_by_session[sid] = (e.get("totalLinesAdded") or 0, e.get("totalLinesRemoved") or 0)
            if t == "permission-mode" and e.get("permissionMode") == "plan":
                plan_mode_sessions.add(sid)
            if t == "system" and e.get("subtype") == "stop_hook_summary" and (e.get("hookCount") or 0) > 0:
                hook_sessions.add(sid)
            if not d or not in_period(d):
                continue
            if t == "assistant":
                ql = e.get("quotaLimits") or {}
                if ql.get("status") == "rejected":
                    limit_days.add(d)
                    limit_events += 1
                elif "warning" in str(ql.get("status", "")):
                    warn_days.add(d)
                msg = e.get("message") or {}
                if msg.get("id") and msg.get("usage"):
                    usage_by_msg[msg["id"]] = msg["usage"]
                for b in msg.get("content") or []:
                    if not isinstance(b, dict) or b.get("type") != "tool_use":
                        continue
                    name, inp = b.get("name", ""), b.get("input") or {}
                    tool_uses["mcp:" + name.split("__")[1] if name.startswith("mcp__") else name] += 1
                    if name.startswith("mcp__"):
                        mcp_servers[name.split("__")[1]] += 1
                    if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                        edit_ids.add(b.get("id"))
                        if inp.get("file_path"):
                            files_edited.add(str(inp["file_path"]).lower())
                    if name in ("Bash", "PowerShell") and re.search(r"\bgit\b[^\n]*\bcommit\b", str(inp.get("command", ""))):
                        commits += 1
                    if name == "Skill":
                        skills_used[str(inp.get("skill"))] += 1
                    if name in ("Agent", "Task"):
                        subagent_calls += 1
                    if name in ("WebFetch", "WebSearch"):
                        web_calls += 1
                    if name in ("EnterPlanMode", "ExitPlanMode"):
                        plan_mode_sessions.add(sid)
            if t != "user":
                continue
            c = (e.get("message") or {}).get("content")
            if isinstance(c, list):
                if e.get("toolDenialKind"):
                    denials[e["toolDenialKind"]] += 1
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in edit_ids:
                        if e.get("toolDenialKind") == "user-rejected":
                            rejected_edits.add(b["tool_use_id"])
                if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                    continue
            if e.get("isSidechain") or e.get("isMeta") or e.get("isCompactSummary"):
                continue
            if e.get("turnOrigin") == "task_notification":
                continue
            txt = text_of(c).strip()
            if not txt or txt.startswith("Below is a conversation log"):
                continue
            m = re.match(r"<([a-zA-Z_-]+)", txt)
            if m and m.group(1) in SKIP_TAGS:
                continue
            is_slash = bool(m and m.group(1) in ("command-name", "command-message"))
            if is_slash:
                name_m = re.search(r"<command-name>/?([^<]+)</command-name>", txt)
                skills_used["/" + (name_m.group(1).strip() if name_m else "?")] += 1
            has_image = isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "image" for b in c)
            images += has_image
            clean = re.sub(r"</?pasted_content[^>]*>", "", txt)
            prompts.append({
                "ts": local(ts).isoformat(), "date": d.isoformat(), "hour": local(ts).hour, "session": sid,
                "project": os.path.basename((e.get("cwd") or "").rstrip("\\/")) or "?", "entry": e.get("entrypoint"),
                "source": e.get("promptSource") or "", "slash": int(is_slash), "image": int(has_image),
                "pasted": int("<pasted_content" in txt), "words": len(clean.split()), "text": clean,
            })

if not prompts:
    raise SystemExit(f"No prompts found between {START} and {END} in {ROOT}.")

prompts.sort(key=lambda p: p["ts"])
by_session = collections.defaultdict(list)
for p in prompts:
    by_session[p["session"]].append(p)
for ps in by_session.values():
    for i, p in enumerate(ps):
        p["followup"] = int(i > 0)
        p["correction"] = int(i > 0 and bool(CORRECT_RE.search(p["text"][:200])))
        p["format"] = int(bool(FORMAT_RE.search(p["text"])))
        p["context"] = int(bool(CONTEXT_RE.search(p["text"])))
        p["fileref"] = int(bool(re.search(r"@[\w./\\-]+\.\w+|[A-Za-z]:\\[\w\\.-]+|\b[\w/-]+\.(php|tsx?|jsx?|py|md|json|ya?ml|css|sql|go|rb|java|cs)\b", p["text"])))
        hits = [k for k, r in SECRET_RES.items() if r.search(p["text"])]
        if any(luhn(x) for x in CARD_RE.findall(p["text"])):
            hits.append("card_number")
        if len(set(EMAIL_RE.findall(p["text"]))) >= 5:
            hits.append("bulk_emails")
        p["secrets"] = ";".join(hits)

all_days = [START + timedelta(n) for n in range((END - START).days + 1)]
working = [d for d in all_days if d.weekday() < 5]
active = sorted({date.fromisoformat(p["date"]) for p in prompts})
active_working = [d for d in active if d.weekday() < 5]
streak = best = 0
prev = None
for d in active:
    streak = streak + 1 if prev and (d - prev).days == 1 else 1
    best, prev = max(best, streak), d
followups = [p for p in prompts if p["followup"]]
sess_lens = [len(v) for v in by_session.values()]


def half_stats(first):
    ps = [p for p in prompts if (date.fromisoformat(p["date"]) <= MID) == first]
    wd = [d for d in working if (d <= MID) == first]
    ad = {p["date"] for p in ps if date.fromisoformat(p["date"]).weekday() < 5}
    fu = [p for p in ps if p["followup"]]
    return {"prompts": len(ps), "working_days": len(wd), "active_working_days": len(ad),
            "active_day_rate": round(len(ad) / len(wd), 3) if wd else 0,
            "prompts_per_working_day": round(len(ps) / len(wd), 2) if wd else 0,
            "correction_rate": round(sum(p["correction"] for p in fu) / len(fu), 3) if fu else 0,
            "sessions": len({p["session"] for p in ps})}


weekly = collections.OrderedDict()
for d in all_days:
    weekly.setdefault((d - timedelta(d.weekday())).isoformat(), {"prompts": 0, "active_days": 0})
for p in prompts:
    d = date.fromisoformat(p["date"])
    weekly[(d - timedelta(d.weekday())).isoformat()]["prompts"] += 1
for d in active:
    weekly[(d - timedelta(d.weekday())).isoformat()]["active_days"] += 1

tok = collections.Counter()
for u in usage_by_msg.values():
    for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        tok[k] += u.get(k) or 0
period_sessions = set(by_session)
capabilities = {
    "MCP tools": sum(mcp_servers.values()) > 0,
    "Skills / slash commands": len(skills_used) > 0,
    "Subagents": subagent_calls > 0,
    "Plan mode": len(plan_mode_sessions & period_sessions) > 0,
    "Web fetch / search": web_calls > 0,
    "Hooks": len(hook_sessions & period_sessions) > 0,
    "Image input": images > 0,
    "File references in prompts": any(p["fileref"] for p in prompts),
}
n = len(prompts)
metrics = {
    "period": [START.isoformat(), END.isoformat()], "timezone": TZ_NAME,
    "transcript_files": len(files), "earliest_transcript_event": earliest_event.isoformat() if earliest_event else None,
    "period_truncated": bool(earliest_event and earliest_event > START),
    "calendar_days": len(all_days), "working_days": len(working),
    "active_days": len(active), "active_working_days": len(active_working),
    "weekend_active_days": len(active) - len(active_working),
    "active_day_rate": round(len(active_working) / len(working), 3) if working else 0,
    "longest_streak": best, "first_active": active[0].isoformat(), "last_active": active[-1].isoformat(),
    "prompts": n, "sessions": len(by_session),
    "prompts_per_active_day": round(n / len(active), 2),
    "prompts_per_working_day": round(n / len(working), 2) if working else 0,
    "avg_prompts_per_session": round(statistics.mean(sess_lens), 2),
    "median_prompts_per_session": statistics.median(sess_lens),
    "max_prompts_per_session": max(sess_lens),
    "one_prompt_sessions_pct": round(sum(1 for x in sess_lens if x == 1) / len(sess_lens), 3),
    "prompt_source": collections.Counter(p["source"] or "unknown" for p in prompts),
    "projects": collections.Counter(p["project"] for p in prompts).most_common(),
    "hour_profile": dict(sorted(collections.Counter(p["hour"] for p in prompts).items())),
    "weekday_profile": {k: collections.Counter(date.fromisoformat(p["date"]).strftime("%a") for p in prompts).get(k, 0)
                        for k in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")},
    "weekly": weekly,
    "halves": {"first": half_stats(True), "second": half_stats(False), "split_after": MID.isoformat()},
    "signals": {
        "median_words": statistics.median([p["words"] for p in prompts]),
        "pct_30plus_words": round(sum(p["words"] >= 30 for p in prompts) / n, 3),
        "pct_sessions_with_file_or_image": round(sum(any(p["fileref"] or p["image"] or p["pasted"] for p in v) for v in by_session.values()) / len(by_session), 3),
        "pct_format_spec": round(sum(p["format"] for p in prompts) / n, 3),
        "pct_context": round(sum(p["context"] for p in prompts) / n, 3),
        "correction_rate": round(sum(p["correction"] for p in followups) / len(followups), 3) if followups else 0,
        "pct_suggestion_accepted": round(sum(p["source"] == "suggestion_accepted" for p in prompts) / n, 3),
        "pct_slash": round(sum(p["slash"] for p in prompts) / n, 3),
    },
    "capabilities": capabilities,
    "breadth": sum(capabilities.values()), "detectable_capabilities": len(capabilities),
    "skills_used": skills_used.most_common(), "mcp_servers": mcp_servers.most_common(),
    "subagent_calls": subagent_calls, "web_calls": web_calls, "images": images,
    "plan_mode_sessions": len(plan_mode_sessions & period_sessions), "hook_sessions": len(hook_sessions & period_sessions),
    "tool_calls_top": tool_uses.most_common(20), "tool_calls_total": sum(tool_uses.values()),
    "files_edited": len(files_edited), "edit_calls": len(edit_ids), "edit_rejected": len(rejected_edits),
    "edit_rejection_rate": round(len(rejected_edits) / len(edit_ids), 3) if edit_ids else 0,
    "git_commit_commands": commits, "prs_linked": len(prs),
    "lines_added": sum(v[0] for s, v in lines_by_session.items() if s in period_sessions),
    "lines_removed": sum(v[1] for s, v in lines_by_session.items() if s in period_sessions),
    "tokens": dict(tok),
    "limit_hit_days": sorted(d.isoformat() for d in limit_days), "limit_rejected_events": limit_events,
    "limit_warning_days": sorted(d.isoformat() for d in warn_days),
    "tool_denials": denials,
    "data_handling": collections.Counter(s for p in prompts for s in p["secrets"].split(";") if s),
    "data_handling_where": [(p["date"], p["project"], p["secrets"]) for p in prompts if p["secrets"]],
}
with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as fh:
    json.dump(metrics, fh, indent=1, default=str)
with open(os.path.join(OUT, "prompts.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(prompts[0].keys()))
    w.writeheader()
    w.writerows(prompts)

random.seed(61)
cands = [s for s, ps in by_session.items() if any(p["words"] >= 6 and not p["slash"] for p in ps)]
by_week = collections.defaultdict(list)
for s in cands:
    d = date.fromisoformat(by_session[s][0]["date"])
    by_week[(d - timedelta(d.weekday())).isoformat()].append(s)
target = min(args.sample, len(cands))
chosen = []
for ss in by_week.values():
    chosen += random.sample(ss, min(max(1, round(target * len(ss) / len(cands))), len(ss)))
chosen = sorted(chosen[:target], key=lambda s: by_session[s][0]["ts"])


def redact(t: str) -> str:
    for r in SECRET_RES.values():
        t = r.sub("[REDACTED]", t)
    return EMAIL_RE.sub("[email]", t)


with open(os.path.join(OUT, "sample.txt"), "w", encoding="utf-8") as fh:
    for i, s in enumerate(chosen, 1):
        ps = [p for p in by_session[s] if not p["slash"]] or by_session[s]
        fh.write(f"=== S{i:02d} {ps[0]['date']} {ps[0]['project']} prompts={len(by_session[s])}\n")
        fh.write("OPEN: " + redact(ps[0]["text"][:1500]) + "\n")
        for p in ps[1:5]:
            fh.write("  FU: " + redact(p["text"][:300]).replace("\n", " ") + "\n")
        fh.write("\n")
with open(os.path.join(OUT, "sample_index.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["sample_id", "session", "date", "project", "prompts"])
    for i, s in enumerate(chosen, 1):
        w.writerow([f"S{i:02d}", s, by_session[s][0]["date"], by_session[s][0]["project"], len(by_session[s])])

print(json.dumps({k: metrics[k] for k in ["period", "earliest_transcript_event", "period_truncated", "active_days", "working_days",
                                          "active_day_rate", "prompts", "sessions", "breadth", "limit_hit_days"]}, default=str))
print(f"sampled {len(chosen)} of {len(cands)} candidate sessions -> sample.txt")
