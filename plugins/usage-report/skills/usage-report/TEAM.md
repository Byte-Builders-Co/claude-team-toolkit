# Team mode (for the team lead)

Run as `/usage-report team <month folder>`, for example `/usage-report team "D:/Reports/2026-12"`.

## Folder layout the team uses

```
Reports/
  history.json            all months, read by the team dashboard (team_summary.py keeps it up to date)
  2026-12/
    Avinash/  metrics.json  scores.json  claude-usage-report_….docx
    Hitarth/  …
```

Each member copies only these three files. Never accept `prompts.csv`, `sample.txt`, `narrative.json` or `suggested/`.

## Steps

```
- [ ] 1. python SKILL_DIR/scripts/team_summary.py --month-dir "<month folder>" --label YYYY-MM --history "<Reports>/history.json"
- [ ] 2. Read the printed table, <month folder>/team_summary.md and history.json (earlier months).
- [ ] 3. Write <month folder>/team_note.md in English for the lead (not shared with the team as-is):
         - 3-line bottom line: what moved since last month, team-wide
         - who met their targets (from each scores.json "progress.targets") and who needs a 1:1 this month
         - one team-wide focus for next month (one or two changes only, so the effect can be measured)
         - data-handling flags that need follow-up (counts and dates only)
         - any method change (v1 → v2) that makes a jump look bigger or smaller than it is
- [ ] 4. Tell the lead to republish the team dashboard with the new history.json.
```

## Rules

- "–" / null means not measured, never zero. Don't compare a v2 KPI with a v1 month.
- No ranking or league tables. Show each person's change against their own last month.
- Read trends over 2–3 months, not single months (holidays, project phases, ~45 judged sessions).
- Volume (prompts, lines added) is not a target.
