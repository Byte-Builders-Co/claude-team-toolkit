"""Personal Claude Code usage metrics (PERSONAL.md steps 1-4a) and the judged sample.  Method v2.

Usage:
  python analyze.py --out DIR [--month YYYY-MM | --start YYYY-MM-DD --end YYYY-MM-DD]
                    [--config team-config.json] [--tz Area/City] [--workdays Mon-Sat] [--holidays 2026-11-09,...]
Defaults: the 30 days ending yesterday; settings from team-config.json next to this skill when present.
Writes (OUT):
  metrics.json            aggregates only, safe to share
  prompts.csv             raw prompt text            (PRIVATE)
  sample.txt              judged sample + outcomes   (PRIVATE)
  sample_index.csv        sample ids -> sessions     (PRIVATE)
  repeated_phrases.json   phrases repeated across sessions, for the CLAUDE.md snippet (PRIVATE)
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse, json, glob, os, re, csv, collections, statistics, random, subprocess, calendar
from datetime import datetime, date, timedelta

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METHOD_VERSION = 2

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--month", help="calendar month YYYY-MM; overrides --start/--end")
ap.add_argument("--start")
ap.add_argument("--end")
ap.add_argument("--tz")
ap.add_argument("--config", default=os.path.join(SKILL_DIR, "team-config.json"))
ap.add_argument("--workdays", help="e.g. Mon-Fri, Mon-Sat or Mon,Tue,Thu")
ap.add_argument("--holidays", help="comma-separated YYYY-MM-DD")
ap.add_argument("--sample", type=int)
args = ap.parse_args()

CFG = {}
if args.config and os.path.exists(args.config):
    with open(args.config, encoding="utf-8") as fh:
        CFG = json.load(fh)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_workdays(v):
    if not v:
        return [0, 1, 2, 3, 4]
    if isinstance(v, list):
        return sorted(DAYS.index(x[:3].title()) for x in v)
    if "-" in v:
        a, b = (DAYS.index(x.strip()[:3].title()) for x in v.split("-"))
        return list(range(a, b + 1))
    return sorted(DAYS.index(x.strip()[:3].title()) for x in v.split(","))


WORKDAYS = parse_workdays(args.workdays or CFG.get("workdays"))
HOLIDAYS = {date.fromisoformat(x.strip()) for x in (args.holidays.split(",") if args.holidays else CFG.get("holidays", [])) if x.strip()}
SAMPLE = args.sample or CFG.get("sample_size") or 45

OUT = os.path.abspath(os.path.expanduser(args.out))
os.makedirs(OUT, exist_ok=True)
TZ_ARG = args.tz or CFG.get("timezone")
TZ = None
if TZ_ARG:
    try:
        from zoneinfo import ZoneInfo
        TZ = ZoneInfo(TZ_ARG)
    except Exception:
        print(f"WARNING: time zone {TZ_ARG} unavailable (pip install tzdata); using the system offset")
TZ = TZ or datetime.now().astimezone().tzinfo
TZ_NAME = TZ_ARG or str(datetime.now().astimezone().tzname())
if args.month:
    y, mo = map(int, args.month.split("-"))
    START, END = date(y, mo, 1), date(y, mo, calendar.monthrange(y, mo)[1])
else:
    END = date.fromisoformat(args.end) if args.end else datetime.now(TZ).date() - timedelta(1)
    START = date.fromisoformat(args.start) if args.start else END - timedelta(29)
MID = START + (END - START) / 2
HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, ".claude", "projects")

SKIP_TAGS = ("task-notification", "bash-input", "bash-stdout", "bash-stderr", "local-command-stdout",
             "local-command-caveat", "system-reminder", "artifact-content-authored-by-others")
# Slash commands that manage the session rather than ask for work. Counted separately, never as prompts.
HOUSEKEEPING = {"clear", "compact", "login", "logout", "restart", "exit", "quit", "resume", "config", "status", "model",
                "cost", "help", "doctor", "permissions", "memory", "init", "ide", "theme", "vim", "terminal-setup",
                "fast", "usage", "context", "rewind", "export", "add-dir", "hooks", "agents", "mcp", "plugin", "plugins",
                "upgrade", "bug", "feedback", "release-notes", "statusline", "output-style", "privacy-settings", "todos"}
IDE_RE = re.compile(r"<(ide_[a-z_]+)\b[^>]*>.*?</\1>|<ide_[a-z_]+\b[^>]*/>", re.S | re.I)
PASTE_RE = re.compile(r"<pasted_content[^>]*>.*?</pasted_content[^>]*>", re.S | re.I)
FORMAT_RE = re.compile(r"\b(table|bullet|list|json|csv|markdown|steps?|checklist|summar(y|ise|ize)|in \d+ words|one line|short|concise|diff|pr description|commit message|format|report)\b", re.I)
CONTEXT_RE = re.compile(r"\b(because|so that|for (our|my|the) |goal|context|background|currently|we (use|have|are)|I (want|need|am trying)|the reason|users? (can|should)|client|customer|production|prod|staging|kyunki|isliye|taaki)\b", re.I)
DONE_RE = re.compile(r"(done when|should (now )?(show|display|pass|work|be|look|open|return)|expected|verify|confirm|make sure|ensure|run (the )?(tests?|lint|build|pest|phpunit|phpstan|playwright)|tests? (must |should )?pass|until (it|the|all)|acceptance|must (pass|show|work)|check (that|in the browser|on mobile)|at \d{3,4}px|screenshot|hona chahiye|dikhna chahiye|chalna chahiye|pass hon?a? chahiye)", re.I)
CORRECT_RE = re.compile(r"^\s*(no\b|nope|wrong|that'?s (not|wrong)|not what i|try again|still (not|getting|failing|same|show)|doesn'?t work|didn'?t work|it'?s not working|not work(ing)? proper|again\b|same (error|issue|problem)|you (missed|forgot|didn'?t)|abhi bhi|ab bhi|fir se|phir se|nahi (hua|ho raha|chal)|kaam nahi)", re.I)
LOG_RE = re.compile(r"(error|exception|traceback|warning|failed|fatal|sqlstate|stack trace|npm err|at [\w.$<>]+ \(|\.php:\d+|\.tsx?:\d+|\.js:\d+|line \d+|exit code|undefined|null)", re.I)
HINGLISH_RE = re.compile(r"\b(kro|karo|krna|karna|kar do|krdo|nahi|nai|hai|hain|mujhe|esko|isko|usko|yaar|bhai|kya|kyu|kyun|ye|yeh|wo|woh|wala|wali|chahiye|aya|aaya|thik|theek|accha|acha|matlab|abhi|bhi|sab|sabhi)\b", re.I)
VERIFY_CMD_RE = re.compile(r"\b(test|tests|pest|phpunit|jest|vitest|playwright|pytest|lint|eslint|phpstan|larastan|tsc|pint|check:fix|typecheck|type-check|types|cargo test|go test|build)\b", re.I)
SECRET_RES = {
    "api_key_or_token": re.compile(r"(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})"),
    "password": re.compile(r"((password|passwd|pwd|DB_PASSWORD|secret)\s*[:=]\s*\S{4,}|--password[= ]\S{4,}"
                           r"|\b(mysql|mysqldump|mariadb)\b[^\n]*\s(?-i:-p)['\"]?[^\s'\"]{4,}|://[^\s:/@]+:[^\s@/]{4,}@)", re.I),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RISKY_PREFIX = re.compile(r"^(rm|del|rmdir|rd|git (push|reset|clean|rebase|checkout|branch -D)|sudo|curl|wget|ssh|scp|format|shutdown|kill|taskkill|docker (rm|system)|mysql|psql|Remove-Item)\b", re.I)


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


def is_workday(d: date) -> bool:
    return d.weekday() in WORKDAYS and d not in HOLIDAYS


def new_sess():
    return {"edits": 0, "files": set(), "verify_runs": 0, "verify_after_edit": False, "rejections": 0,
            "limit_hits": 0, "interrupts": 0, "output_tokens": 0, "cwd": None}


files = glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True)
prompts, tool_uses, usage_by_msg = [], collections.Counter(), {}
edit_ids, rejected_edits, files_edited = set(), set(), set()
commits, prs, limit_days, limit_events, warn_days = 0, set(), set(), 0, set()
lines_by_session, hook_sessions, plan_mode_sessions = {}, set(), set()
skills_used, mcp_servers, subagent_calls, web_calls, images = collections.Counter(), collections.Counter(), 0, 0, 0
housekeeping = collections.Counter()
denials = collections.Counter()
cmd_by_id, denied_ids = {}, set()
sess = collections.defaultdict(new_sess)
msg_session = {}
earliest_event = None
cwd_prompts = collections.Counter()

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
                S = sess[sid]
                ql = e.get("quotaLimits") or {}
                if ql.get("status") == "rejected":
                    limit_days.add(d)
                    limit_events += 1
                    S["limit_hits"] += 1
                elif "warning" in str(ql.get("status", "")):
                    warn_days.add(d)
                msg = e.get("message") or {}
                if msg.get("id") and msg.get("usage"):
                    usage_by_msg[msg["id"]] = msg["usage"]
                    msg_session[msg["id"]] = sid
                for b in msg.get("content") or []:
                    if not isinstance(b, dict) or b.get("type") != "tool_use":
                        continue
                    name, inp = b.get("name", ""), b.get("input") or {}
                    tool_uses["mcp:" + name.split("__")[1] if name.startswith("mcp__") else name] += 1
                    if name.startswith("mcp__"):
                        mcp_servers[name.split("__")[1]] += 1
                    if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                        edit_ids.add(b.get("id"))
                        S["edits"] += 1
                        S["verify_after_edit"] = False
                        if inp.get("file_path"):
                            files_edited.add(str(inp["file_path"]).lower())
                            S["files"].add(str(inp["file_path"]).lower())
                    if name in ("Bash", "PowerShell"):
                        cmd = str(inp.get("command", "")).strip()
                        cmd_by_id[b.get("id")] = cmd
                        if re.search(r"\bgit\b[^\n]*\bcommit\b", cmd):
                            commits += 1
                        if VERIFY_CMD_RE.search(cmd.split("\n")[0][:200]):
                            S["verify_runs"] += 1
                            if S["edits"]:
                                S["verify_after_edit"] = True
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
                    if e["toolDenialKind"] == "user-rejected" and not e.get("isSidechain"):
                        sess[sid]["rejections"] += 1
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        if e.get("toolDenialKind"):
                            denied_ids.add(b.get("tool_use_id"))
                        if b.get("tool_use_id") in edit_ids and e.get("toolDenialKind") == "user-rejected":
                            rejected_edits.add(b["tool_use_id"])
                if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                    continue
            if e.get("isSidechain") or e.get("isMeta") or e.get("isCompactSummary"):
                continue
            if e.get("turnOrigin") == "task_notification":
                continue
            raw = text_of(c)
            txt = IDE_RE.sub("", raw).strip()          # A4: drop IDE auto-attached context
            if not txt or txt.startswith("Below is a conversation log"):
                continue
            if txt.startswith("[Request interrupted"):  # interrupt marker, not a prompt
                sess[sid]["interrupts"] += 1
                continue
            m = re.match(r"<([a-zA-Z_-]+)", txt)
            if m and m.group(1) in SKIP_TAGS:
                continue
            is_slash = bool(m and m.group(1) in ("command-name", "command-message"))
            if is_slash:
                name_m = re.search(r"<command-name>/?([^<]+)</command-name>", txt)
                cmd_name = name_m.group(1).strip() if name_m else "?"
                if cmd_name.lower() in HOUSEKEEPING:        # A1: housekeeping is not a prompt
                    housekeeping["/" + cmd_name.lower()] += 1
                    continue
                skills_used["/" + cmd_name] += 1
            has_image = isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "image" for b in c)
            images += has_image
            own = PASTE_RE.sub(" ", txt)
            clean = re.sub(r"</?pasted_content[^>]*>", "", txt)
            own_words = len(re.sub(r"\[Image[^\]]*\]", " ", own).split())
            log_hits = len(LOG_RE.findall(clean))
            looks_log = ("<pasted_content" in txt) or (clean.count("\n") >= 4 and log_hits >= 2)
            cwd = e.get("cwd") or ""
            cwd_prompts[cwd] += 1
            sess[sid]["cwd"] = sess[sid]["cwd"] or cwd
            prompts.append({
                "ts": local(ts).isoformat(), "date": d.isoformat(), "hour": local(ts).hour, "session": sid,
                "project": os.path.basename(cwd.rstrip("\\/")) or "?", "entry": e.get("entrypoint"),
                "source": e.get("promptSource") or "", "slash": int(is_slash), "image": int(has_image),
                "pasted": int("<pasted_content" in txt), "words": len(clean.split()), "own_words": own_words,
                "bare_paste": int(looks_log and own_words < 6 and not is_slash),
                "image_only": int(has_image and own_words < 4),
                "hinglish": int(len(HINGLISH_RE.findall(own)) >= 2), "text": clean,
            })

if not prompts:
    raise SystemExit(f"No prompts found between {START} and {END} in {ROOT}.")

for mid, u in usage_by_msg.items():
    sess[msg_session[mid]]["output_tokens"] += u.get("output_tokens") or 0

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
        p["done_check"] = int(bool(DONE_RE.search(PASTE_RE.sub(" ", p["text"]))))
        p["fileref"] = int(bool(re.search(r"@[\w./\\-]+\.\w+|[A-Za-z]:\\[\w\\.-]+|\b[\w/-]+\.(php|tsx?|jsx?|py|md|json|ya?ml|css|sql|go|rb|java|cs|vue)\b", p["text"])))
        hits = [k for k, r in SECRET_RES.items() if r.search(p["text"])]
        if any(luhn(x) for x in CARD_RE.findall(p["text"])):
            hits.append("card_number")
        if len(set(EMAIL_RE.findall(p["text"]))) >= 5:
            hits.append("bulk_emails")
        p["secrets"] = ";".join(hits)

all_days = [START + timedelta(n) for n in range((END - START).days + 1)]
working = [d for d in all_days if is_workday(d)]
active = sorted({date.fromisoformat(p["date"]) for p in prompts})
active_working = [d for d in active if is_workday(d)]
streak = best = 0
prev = None
for d in active:
    streak = streak + 1 if prev and (d - prev).days == 1 else 1
    best, prev = max(best, streak), d
followups = [p for p in prompts if p["followup"]]
openers = [p for p in prompts if not p["followup"]]
sess_lens = [len(v) for v in by_session.values()]


def half_stats(first):
    ps = [p for p in prompts if (date.fromisoformat(p["date"]) <= MID) == first]
    wd = [d for d in working if (d <= MID) == first]
    ad = {p["date"] for p in ps if is_workday(date.fromisoformat(p["date"]))}
    fu = [p for p in ps if p["followup"]]
    return {"prompts": len(ps), "working_days": len(wd), "active_working_days": len(ad),
            "active_day_rate": round(len(ad) / len(wd), 3) if wd else 0,
            "prompts_per_working_day": round(len(ps) / len(wd), 2) if wd else 0,
            "correction_rate": round(sum(p["correction"] for p in fu) / len(fu), 3) if fu else 0,
            "pct_done_check": round(sum(p["done_check"] for p in ps) / len(ps), 3) if ps else 0,
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

# ---- practices (method v2) -------------------------------------------------------------
edit_sessions = [s for s in period_sessions if sess[s]["edits"] > 0]
verified = [s for s in edit_sessions if sess[s]["verify_runs"] > 0]
big = [s for s in period_sessions if len(sess[s]["files"]) >= 3]
big_planned = [s for s in big if s in plan_mode_sessions]
long_sessions = [s for s, ps in by_session.items() if len(ps) > 30]


# ---- configuration found on disk (A5, A7) --------------------------------------------
def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


user_settings = load_json(os.path.join(HOME, ".claude", "settings.json")) or {}
cleanup_days = user_settings.get("cleanupPeriodDays")
top_cwds = [c for c, _ in cwd_prompts.most_common(12) if c and os.path.isdir(c)]
project_setup = []
for c in top_cwds:
    ps_ = [load_json(os.path.join(c, ".claude", n)) or {} for n in ("settings.json", "settings.local.json")]
    project_setup.append({
        "project": os.path.basename(c.rstrip("\\/")), "prompts": cwd_prompts[c],
        "claude_md": os.path.exists(os.path.join(c, "CLAUDE.md")) or os.path.exists(os.path.join(c, ".claude", "CLAUDE.md")),
        "hooks": any(bool(s.get("hooks")) for s in ps_),
        "allowlist": sum(len((s.get("permissions") or {}).get("allow") or []) for s in ps_),
    })
hooks_configured = {
    "user_settings": bool(user_settings.get("hooks")),
    "projects": sum(1 for x in project_setup if x["hooks"]),
    "prompt_coach": os.path.exists(os.path.join(HOME, ".claude", "prompt-coach", "profile.json")),
}

# Prompt-coach log (no prompt text in it)
coach = collections.Counter()
log_path = os.path.join(HOME, ".claude", "prompt-coach", "log.jsonl")
if os.path.exists(log_path):
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
                if in_period(local(r["ts"]).date()):
                    coach["checked"] += 1
                    coach[r.get("action", "none")] += 1
            except Exception:
                continue


# A8: the person's own commits in the main projects (git log by their configured email)
def git(c, *a):
    try:
        return subprocess.run(["git", "-C", c, *a], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


own_commits, own_commit_projects = 0, 0
for c in top_cwds:
    if not os.path.isdir(os.path.join(c, ".git")):
        continue
    email = git(c, "config", "user.email")
    if not email:
        continue
    out = git(c, "log", "--all", "--no-merges", f"--author={email}", f"--since={START.isoformat()}",
              f"--until={(END + timedelta(1)).isoformat()}", "--format=%H")
    own_commits += len([x for x in out.splitlines() if x])
    own_commit_projects += 1

# B4: command prefixes the person ran often (and never denied) -> allowlist candidates
TOOL_FIRST = re.compile(r"^(npm|npx|pnpm|yarn|bun|node|php|php\.bat|composer|python|python3|py|pip|pytest|gh|go|cargo|dotnet|flutter|dart|make|docker|"
                        r"(\./)?vendor/bin/\w+|(\./)?node_modules/\.bin/\w+|git)$", re.I)
GIT_SAFE = {"status", "diff", "log", "show", "add", "commit", "branch", "fetch", "pull", "stash", "switch", "remote", "rev-parse", "ls-files", "blame"}
prefixes = collections.Counter()
for tid, cmd in cmd_by_id.items():
    if tid in denied_ids or not cmd:
        continue
    for seg in re.split(r"\s*(?:&&|\|\||\||;)\s*", cmd.split("\n")[0].strip()):
        toks = seg.split()
        if not toks or toks[0] in ("cd", "export", "set", "&") or re.match(r"^\w+=", toks[0]):
            continue
        if RISKY_PREFIX.match(seg) or not TOOL_FIRST.match(toks[0].replace("\\", "/")):
            break
        if toks[0].lower() == "git" and (len(toks) < 2 or toks[1] not in GIT_SAFE):
            break
        sub = toks[1] if len(toks) > 1 and re.match(r"^[\w:.-]+$", toks[1]) and not toks[1].startswith("-") else ""
        prefixes[(toks[0].replace("\\", "/") + " " + sub).strip()] += 1
        break

capabilities = {
    "MCP tools": sum(mcp_servers.values()) > 0,
    "Skills / slash commands": len(skills_used) > 0,
    "Subagents": subagent_calls > 0,
    "Plan mode": len(plan_mode_sessions & period_sessions) > 0,
    "Web fetch / search": web_calls > 0,
    "Hooks": len(hook_sessions & period_sessions) > 0 or any(hooks_configured.values()),
    "Image input": images > 0,
    "File references in prompts": any(p["fileref"] for p in prompts),
}
n = len(prompts)
quick = [p for p in openers if p["own_words"] < 12]


def rate(xs, key):
    return round(sum(p[key] for p in xs) / len(xs), 3) if xs else 0


metrics = {
    "method_version": METHOD_VERSION,
    "period": [START.isoformat(), END.isoformat()], "timezone": TZ_NAME,
    "workdays": [DAYS[i] for i in WORKDAYS], "holidays_in_period": sorted(d.isoformat() for d in HOLIDAYS if in_period(d)),
    "transcript_files": len(files), "earliest_transcript_event": earliest_event.isoformat() if earliest_event else None,
    "period_truncated": bool(earliest_event and earliest_event > START),
    "cleanup_period_days": cleanup_days,
    "calendar_days": len(all_days), "working_days": len(working),
    "active_days": len(active), "active_working_days": len(active_working),
    "non_working_active_days": len(active) - len(active_working),
    "weekend_active_days": len(active) - len(active_working),
    "active_day_rate": round(len(active_working) / len(working), 3) if working else 0,
    "longest_streak": best, "first_active": active[0].isoformat(), "last_active": active[-1].isoformat(),
    "prompts": n, "sessions": len(by_session),
    "housekeeping_commands": dict(housekeeping.most_common()),
    "interrupts": sum(sess[s]["interrupts"] for s in period_sessions),
    "prompts_per_active_day": round(n / len(active), 2),
    "prompts_per_working_day": round(n / len(working), 2) if working else 0,
    "avg_prompts_per_session": round(statistics.mean(sess_lens), 2),
    "median_prompts_per_session": statistics.median(sess_lens),
    "max_prompts_per_session": max(sess_lens),
    "one_prompt_sessions_pct": round(sum(1 for x in sess_lens if x == 1) / len(sess_lens), 3),
    "pct_sessions_over_30": round(len(long_sessions) / len(by_session), 3),
    "pct_prompts_in_long_sessions": round(sum(len(by_session[s]) for s in long_sessions) / n, 3),
    "prompt_source": collections.Counter(p["source"] or "unknown" for p in prompts),
    "projects": collections.Counter(p["project"] for p in prompts).most_common(),
    "hour_profile": dict(sorted(collections.Counter(p["hour"] for p in prompts).items())),
    "weekday_profile": {k: collections.Counter(date.fromisoformat(p["date"]).strftime("%a") for p in prompts).get(k, 0) for k in DAYS},
    "weekly": weekly,
    "halves": {"first": half_stats(True), "second": half_stats(False), "split_after": MID.isoformat()},
    "signals": {
        "median_words": statistics.median([p["own_words"] for p in prompts]),
        "pct_30plus_words": round(sum(p["own_words"] >= 30 for p in prompts) / n, 3),
        "pct_sessions_with_file_or_image": round(sum(any(p["fileref"] or p["image"] or p["pasted"] for p in v) for v in by_session.values()) / len(by_session), 3),
        "pct_format_spec": rate(prompts, "format"),
        "pct_context": rate(prompts, "context"),
        "pct_done_check": rate(prompts, "done_check"),
        "pct_done_check_openers": rate(openers, "done_check"),
        "pct_bare_paste": rate(prompts, "bare_paste"),
        "pct_image_only": rate(prompts, "image_only"),
        "pct_quick_openers": round(len(quick) / len(openers), 3) if openers else 0,
        "pct_hinglish": rate(prompts, "hinglish"),
        "correction_rate": round(sum(p["correction"] for p in followups) / len(followups), 3) if followups else 0,
        "pct_suggestion_accepted": round(sum(p["source"] == "suggestion_accepted" for p in prompts) / n, 3),
        "pct_slash": rate(prompts, "slash"),
    },
    "practices": {
        "sessions_with_edits": len(edit_sessions),
        "verify_rate": round(len(verified) / len(edit_sessions), 3) if edit_sessions else None,
        "big_sessions": len(big),
        "plan_on_big_rate": round(len(big_planned) / len(big), 3) if big else None,
        "interrupts_per_session": round(sum(sess[s]["interrupts"] for s in period_sessions) / len(period_sessions), 3),
        "rejections_per_session": round(sum(sess[s]["rejections"] for s in period_sessions) / len(period_sessions), 3),
    },
    "capabilities": capabilities,
    "breadth": sum(capabilities.values()), "detectable_capabilities": len(capabilities),
    "skills_used": skills_used.most_common(), "mcp_servers": mcp_servers.most_common(),
    "subagent_calls": subagent_calls, "web_calls": web_calls, "images": images,
    "plan_mode_sessions": len(plan_mode_sessions & period_sessions), "hook_sessions": len(hook_sessions & period_sessions),
    "hooks_configured": hooks_configured, "project_setup": project_setup,
    "prompt_coach": dict(coach),
    "tool_calls_top": tool_uses.most_common(20), "tool_calls_total": sum(tool_uses.values()),
    "files_edited": len(files_edited), "edit_calls": len(edit_ids), "edit_rejected": len(rejected_edits),
    "edit_rejection_rate": round(len(rejected_edits) / len(edit_ids), 3) if edit_ids else 0,
    "git_commit_commands": commits, "claude_commit_commands": commits,
    "own_commits": own_commits if own_commit_projects else None, "own_commit_projects": own_commit_projects,
    "prs_linked": len(prs),
    "lines_added": sum(v[0] for s, v in lines_by_session.items() if s in period_sessions),
    "lines_removed": sum(v[1] for s, v in lines_by_session.items() if s in period_sessions),
    "tokens": dict(tok),
    "limit_hit_days": sorted(d.isoformat() for d in limit_days), "limit_rejected_events": limit_events,
    "limit_warning_days": sorted(d.isoformat() for d in warn_days),
    "tool_denials": denials,
    "allowlist_candidates": [[k, v] for k, v in prefixes.most_common(40) if v >= 5][:20],
    "data_handling": collections.Counter(s for p in prompts for s in p["secrets"].split(";") if s),
    "data_handling_where": [(p["date"], p["project"], p["secrets"]) for p in prompts if p["secrets"]],
}
with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as fh:
    json.dump(metrics, fh, indent=1, default=str)
with open(os.path.join(OUT, "prompts.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(prompts[0].keys()))
    w.writeheader()
    w.writerows(prompts)


def redact(t: str) -> str:
    for r in SECRET_RES.values():
        t = r.sub("[REDACTED]", t)
    return EMAIL_RE.sub("[email]", t)


# ---- B3: phrases repeated across sessions (candidates for CLAUDE.md) ---------------------
STOP = set("the a an and or to of in on for with this that it is are be me my i you your we our please pls do can so all also "
           "then from at as by if not it's its was will just like make want need now same".split())
grams = collections.defaultdict(set)
for s, ps in by_session.items():
    for p in ps:
        if p["slash"]:
            continue
        words = re.findall(r"[a-z][a-z0-9'.-]*", PASTE_RE.sub(" ", p["text"]).lower())[:120]
        for k in (3, 4, 5, 6):
            for i in range(len(words) - k + 1):
                g = words[i:i + k]
                if sum(w not in STOP for w in g) >= 2 and g[0] not in STOP and g[-1] not in STOP:
                    grams[" ".join(g)].add(s)
cands_ph = sorted(((g, len(ss)) for g, ss in grams.items() if len(ss) >= 3), key=lambda x: (-x[1], -len(x[0])))
phrases = []
for g, c in cands_ph:
    if any(g in kept and c <= kc for kept, kc in phrases):
        continue
    phrases.append((g, c))
    if len(phrases) >= 25:
        break
with open(os.path.join(OUT, "repeated_phrases.json"), "w", encoding="utf-8") as fh:
    json.dump([{"phrase": redact(g), "sessions": c} for g, c in phrases], fh, indent=1, ensure_ascii=False)


# ---- judged sample with outcomes (B1) and the most expensive session (B8) ----------------
def outcome(s):
    S, ps = sess[s], by_session[s]
    return (f"OUTCOME: prompts={len(ps)} corrections={sum(p['correction'] for p in ps)} interrupts={S['interrupts']} "
            f"rejections={S['rejections']} limit_hits={S['limit_hits']} files_edited={len(S['files'])} "
            f"verify_runs={S['verify_runs']} verified_after_last_edit={'yes' if S['verify_after_edit'] else 'no'} "
            f"plan_mode={'yes' if s in plan_mode_sessions else 'no'} output_tokens={S['output_tokens']}")


def cost(s):
    S, ps = sess[s], by_session[s]
    return (len(ps) + 3 * sum(p["correction"] for p in ps) + 2 * S["interrupts"] + 2 * S["rejections"]
            + 6 * S["limit_hits"] + S["output_tokens"] / 20000)


random.seed(61)
cands = [s for s, ps in by_session.items() if any(p["own_words"] >= 6 and not p["slash"] for p in ps)]
by_week = collections.defaultdict(list)
for s in cands:
    d = date.fromisoformat(by_session[s][0]["date"])
    by_week[(d - timedelta(d.weekday())).isoformat()].append(s)
target = min(SAMPLE, len(cands))
chosen = []
for ss in by_week.values():
    chosen += random.sample(ss, min(max(1, round(target * len(ss) / len(cands))), len(ss)))
chosen = sorted(chosen[:target], key=lambda s: by_session[s][0]["ts"])
expensive = max((s for s in by_session if len(by_session[s]) >= 5), key=cost, default=None)

with open(os.path.join(OUT, "sample.txt"), "w", encoding="utf-8") as fh:
    for i, s in enumerate(chosen, 1):
        ps = [p for p in by_session[s] if not p["slash"]] or by_session[s]
        fh.write(f"=== S{i:02d} {ps[0]['date']} {ps[0]['project']} prompts={len(by_session[s])}\n")
        fh.write(outcome(s) + "\n")
        fh.write("OPEN: " + redact(ps[0]["text"][:1500]) + "\n")
        for p in ps[1:5]:
            fh.write("  FU: " + redact(p["text"][:300]).replace("\n", " ") + "\n")
        fh.write("\n")
    if expensive:
        ps = [p for p in by_session[expensive] if not p["slash"]] or by_session[expensive]
        fh.write(f"=== EXPENSIVE {ps[0]['date']} {ps[0]['project']} prompts={len(by_session[expensive])}\n")
        fh.write(outcome(expensive) + "\n")
        fh.write("OPEN: " + redact(ps[0]["text"][:1500]) + "\n")
        for p in ps[1:16]:
            fh.write(f"  FU {p['ts'][11:16]}: " + redact(p["text"][:300]).replace("\n", " ") + "\n")
with open(os.path.join(OUT, "sample_index.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["sample_id", "session", "date", "project", "prompts"])
    for i, s in enumerate(chosen, 1):
        w.writerow([f"S{i:02d}", s, by_session[s][0]["date"], by_session[s][0]["project"], len(by_session[s])])

if not cleanup_days or cleanup_days < 90:
    print(f"WARNING: cleanupPeriodDays is {cleanup_days or 'not set (default 30 days)'}. Add \"cleanupPeriodDays\": 90 to ~/.claude/settings.json so next month's report is complete.")
print(json.dumps({k: metrics[k] for k in ["method_version", "period", "workdays", "period_truncated", "active_days", "working_days",
                                          "active_day_rate", "prompts", "sessions", "breadth", "limit_hit_days"]}, default=str))
print(f"sampled {len(chosen)} of {len(cands)} candidate sessions -> sample.txt"
      + (f"; most expensive session: {by_session[expensive][0]['date']} ({len(by_session[expensive])} prompts)" if expensive else ""))
