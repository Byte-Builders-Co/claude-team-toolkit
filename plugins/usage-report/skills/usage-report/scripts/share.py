"""The person's Google Drive share folder: set it once, then upload each month's shareable files.

Usage:
  python share.py --set "G:/My Drive/Avinash"     remember this person's own Drive folder (a shortcut to the folder the lead shared)
  python share.py --set-team-root "G:/My Drive/Claude Reports"   (lead only) the team folder with everyone's sub-folders
  python share.py --show                          print the saved settings
  python share.py --out DIR                       copy this month's shareable files to <share_dir>/<YYYY-MM>/

Only these files are uploaded: metrics.json, scores.json, coach-draft.json and the .docx report.
Raw prompts (prompts.csv, sample.txt, narrative.json, suggested/ ...) are never copied.
Settings live in ~/.claude/usage-report.local.json: {"name", "language", "share_dir"}.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse, glob, json, os, shutil

LOCAL = os.environ.get("USAGE_REPORT_LOCAL") or os.path.join(os.path.expanduser("~"), ".claude", "usage-report.local.json")
SHAREABLE = ["metrics.json", "scores.json", "coach-draft.json"]


def local_cfg():
    try:
        with open(LOCAL, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_local(cfg):
    atomic_json(LOCAL, cfg)


def atomic_json(path, obj):
    """Write to a temp file, then rename, so Drive never syncs a half-written file."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def atomic_copy(src, dst):
    tmp = dst + ".tmp"
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set")
    ap.add_argument("--set-team-root")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    cfg = local_cfg()

    if a.set:
        d = os.path.abspath(os.path.expanduser(a.set))
        if not os.path.isdir(d):
            raise SystemExit(f"Folder not found: {d}\nOpen Google Drive for desktop, make sure the folder the lead shared "
                             "is added to 'My Drive' (right-click > Organise > Add shortcut), and wait for it to appear.")
        if os.path.isdir(os.path.join(d, "_team")):
            raise SystemExit(f"{d} is the lead's team folder. Use your own sub-folder (the one with your name).")
        cfg["share_dir"] = d
        save_local(cfg)
        print(json.dumps({"saved": LOCAL, "share_dir": d}, ensure_ascii=False))
        return

    if a.set_team_root:
        d = os.path.abspath(os.path.expanduser(a.set_team_root))
        if not os.path.isdir(d):
            raise SystemExit(f"Folder not found: {d}. Check that Google Drive for desktop is running and signed in.")
        os.makedirs(os.path.join(d, "_team"), exist_ok=True)
        cfg["team_root"] = d
        save_local(cfg)
        print(json.dumps({"saved": LOCAL, "team_root": d}, ensure_ascii=False))
        return

    if a.show:
        print(json.dumps({"settings_file": LOCAL, **cfg}, indent=1, ensure_ascii=False))
        return

    if not a.out:
        ap.error("use --set, --show or --out")
    out = os.path.abspath(os.path.expanduser(a.out))
    month = os.path.basename(out.rstrip("/\\"))
    share = cfg.get("share_dir")
    if not share:
        print(json.dumps({"uploaded": False, "reason": "no share_dir",
                          "fix": "Run /usage-report share \"<your Google Drive folder>\" once, then /usage-report upload"}))
        return
    if not os.path.isdir(share):
        print(json.dumps({"uploaded": False, "reason": f"share folder not found: {share}",
                          "fix": "Start Google Drive for desktop and check the folder still exists, then /usage-report upload"}))
        return
    dest = os.path.join(share, month)
    os.makedirs(dest, exist_ok=True)
    files = [f for f in SHAREABLE if os.path.exists(os.path.join(out, f))] + \
            [os.path.basename(p) for p in glob.glob(os.path.join(out, "*.docx"))]
    for f in files:
        atomic_copy(os.path.join(out, f), os.path.join(dest, f))
    missing = [f for f in ("metrics.json", "scores.json") if f not in files]
    print(json.dumps({"uploaded": not missing, "to": dest, "files": files, "missing": missing}, ensure_ascii=False))


if __name__ == "__main__":
    main()
