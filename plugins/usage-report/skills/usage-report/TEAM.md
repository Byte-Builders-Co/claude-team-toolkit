# Team mode (for the team lead)

The lead reviews everyone's monthly reports, refreshes the team dashboard, and decides what each person's prompt coach should focus on next. **Nothing reaches a team member's coach until the lead approves it.**

`ROOT` = the team's Google Drive folder on the lead's machine. It is saved in `~/.claude/usage-report.local.json` as `"team_root"`. If it is missing, ask the lead once for the path (for example `G:/My Drive/Claude Reports`) and save it with `python SKILL_DIR/scripts/share.py --set-team-root "<path>"`.

## Google Drive layout

```
Claude Reports/                    owned by the lead
  _team/                           only the lead (never shared)
    history.json  kpi_history.csv  all months, for the dashboard
    2026-12/  team_summary.md  review_input.json  review.md  proposal.json  approved.json
  Avinash/                         shared with Avinash only (Editor)
    2026-12/  metrics.json  scores.json  coach-draft.json  claude-usage-report_….docx    (written by Avinash's report)
    coach/    profile.json  history/rev-N.json                                          (written by approve.py only)
  Hitarth/ …
```

One writer per file: the member writes `<Name>/<YYYY-MM>/`, the lead writes `<Name>/coach/` and `_team/`. Never edit a member's month folder or hand-edit a `profile.json`.

## First time only

Google Drive setup (the lead does this once):
1. In Google Drive, create `Claude Reports` with a sub-folder per person (names as in `team-config.json` > `members`) and `_team`.
2. Share **each person's sub-folder only** with that person, as Editor. Never share `Claude Reports` itself or `_team`.
3. The lead has a sub-folder too and runs `/usage-report share` for it: their own report and coach go through the same review.
4. Tell everyone to do install step 5 in the README (add the shortcut to My Drive, then `/usage-report share`).
5. Holidays: add them to `team-config.json` before the 1st, commit, and ask everyone to update the plugin.

- If `ROOT/_team/history.json` does not exist, copy the existing `history.json` and `kpi_history.csv` (the lead knows where: for Byte-Builders they are in `Downloads/Claude Usages Reports/`) into `ROOT/_team/` before step 1. team_summary.py stops with "STOP: no history" otherwise; never pass `--new-history` unless the lead says the team is brand new.
- The lead's own report works like everyone else's: the lead has a sub-folder too, sets it with `/usage-report share`, and approves their own coach profile in the same proposal.

## `/usage-report team [YYYY-MM]` (default: last month)

```
- [ ] 1. python SKILL_DIR/scripts/team_summary.py --root ROOT --label YYYY-MM
         It prints the KPI table and "MISSING: …". If anyone is missing, say who, and ask whether to wait or continue.
- [ ] 2. Read ROOT/_team/YYYY-MM/review_input.json and ROOT/_team/history.json (earlier months).
- [ ] 3. Refresh the dashboard (team-config "dashboard_url") with ROOT/_team/kpi_history.csv:
         Artifact action "read" on the URL, upload the CSV as an asset of that artifact, point the "kpi_history"
         dataset at the new asset, then check it. If the Artifact tool is not available, tell the lead to do it
         from a Claude Code session that has it.
- [ ] 4. Write ROOT/_team/YYYY-MM/review.md in English for the lead:
         - Bottom line (3 lines): what moved team-wide since last month.
         - Per person, in this order:
           * Improved: KPIs that got better, and last month's targets met (from "progress").
           * Still to work on: the 1-2 KPIs with most room, with the number now and a realistic target.
           * Coach use: from draft.coach_stats (prompts checked, restated, stopped, asked), counts only.
           * Proposed coach change: old -> new focus, block mode, number of tips/templates, and why.
         - One team-wide focus for next month (one or two changes only, so the effect can be measured).
         - Data-handling flags (counts and dates only). Any v1 -> v2 method note.
- [ ] 5. Write ROOT/_team/YYYY-MM/proposal.json: {Name: {focus, tips, templates, settings, message}}.
         Start from each person's draft. Keep at most 3 focus areas (the ones with most room).
         tips in the person's language, templates in simple English, message = one encouraging line in their language.
         settings only when changing something (e.g. {"block_mode": "ask"} once bare pastes are rare).
- [ ] 6. Show the lead a short summary of review.md and the proposed coach changes as a table
         (Name | improved | to work on | focus old -> new | block mode). Ask them to approve, or to say what to change.
```

## `/usage-report approve` (after the lead says yes)

```
- [ ] 1. Apply the lead's edits to proposal.json (only what they asked for).
- [ ] 2. python SKILL_DIR/scripts/approve.py --root ROOT --month YYYY-MM --names all --dry-run
         Show the printed changes. If they match what the lead approved:
- [ ] 3. python SKILL_DIR/scripts/approve.py --root ROOT --month YYYY-MM --names all   (or --names A,B)
- [ ] 4. Tell the lead: each person's coach loads the new profile at their next Claude Code session start
         (once Drive has synced) and tells them once, in their language, what changed.
```

## Rules

- "–" / null means not measured, never zero. Don't compare a v2 KPI with a v1 month.
- No ranking or league tables. Show each person's change against their own last month.
- Read trends over 2–3 months, not single months (holidays, project phases, ~45 judged sessions).
- Volume (prompts, lines added) is not a target.
- Never copy anything from `_team/` into a member's folder except through approve.py.

## Old layout (before Google Drive)

`python SKILL_DIR/scripts/team_summary.py --month-dir "<Reports>/<YYYY-MM>" --label YYYY-MM` still works for folders laid out as `<Reports>/<YYYY-MM>/<Name>/`.
