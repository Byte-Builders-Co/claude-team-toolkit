# Byte-Builders Claude Code toolkit

Two Claude Code plugins for the team, installed from this repo:

| Plugin | What it does | Commands |
|---|---|---|
| **usage-report** | Monthly usage and prompt-quality report with coaching in Hindi (or Gujarati), prompt templates, progress vs last month, and ready-made setup files | `/usage-report` · `/usage-report monthly 2026-12` · `/usage-report team <folder>` (lead) |
| **prompt-coach** | Checks every prompt before Claude works on it. Vague prompts get restated as Goal / Scope / Done when with a short tip; bare pastes are stopped with a one-line fix | `/prompt-coach:p <rough idea>` · `/prompt-coach:setup` |

## Install (once, about 2 minutes)

You need Node.js 18+, Python 3.10+ with `matplotlib` and `tzdata` (`pip install matplotlib tzdata`), and access to this private repo (GitHub login via `gh auth login`, or an SSH key).

1. **Remove the old zip version**, if you have it: delete the folder `~/.claude/skills/claude-usage-report/` (Windows: `%USERPROFILE%\.claude\skills\claude-usage-report\`).
2. In a terminal:
   ```
   claude plugin marketplace add Byte-Builders-Co/claude-team-toolkit
   claude plugin install usage-report@byte-builders-claude
   claude plugin install prompt-coach@byte-builders-claude
   ```
   (Or inside Claude Code: `/plugin marketplace add Byte-Builders-Co/claude-team-toolkit`, then `/plugin install …`.)

   If `marketplace add` fails with "Could not read from remote repository", your SSH key isn't set up for GitHub. Run `gh auth login`, then set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` in your environment and try again. You also need access to the repo: ask the lead to add you.
3. Keep 90 days of history, so monthly reports are complete. Add this to `~/.claude/settings.json`:
   ```json
   { "cleanupPeriodDays": 90 }
   ```
4. Restart Claude Code, then run `/prompt-coach:setup`. If your lead sent you a profile file, run `/prompt-coach:setup import <file>` instead.

## Update (when the lead announces a new version)

```
claude plugin marketplace update byte-builders-claude
claude plugin update usage-report@byte-builders-claude
claude plugin update prompt-coach@byte-builders-claude
```

## Every month (1st working day)

1. Run `/usage-report` in Claude Code. It reports on the previous calendar month, using the team settings in `plugins/usage-report/skills/usage-report/team-config.json` (Mon–Sat, holidays, IST).
2. Copy **only** `metrics.json`, `scores.json` and the `.docx` from `~/Documents/claude-usage-reports/<YYYY-MM>/` to the shared folder `Reports/<YYYY-MM>/<YourName>/`.
3. Open `suggested/` in the same folder: it holds a `CLAUDE.md` snippet, a permissions allowlist and draft slash commands made from your own work. Use what helps.

Never share `prompts.csv`, `sample.txt`, `narrative.json` or `suggested/`. They contain your raw prompts.

## For the lead

- Add holidays to `team-config.json` before the 1st, commit, and ask everyone to update.
- After everyone has submitted: `/usage-report team "<Reports>/<YYYY-MM>"`. This updates `Reports/history.json` (for the team dashboard) and writes `team_summary.md` and `team_note.md`.
- Prompt-coach block mode stops bare pastes for 21 days after setup. Turn it off per person with `/prompt-coach:setup block off`, or set `"block_mode": "ask"`.

## Privacy

- The report reads `~/.claude/projects` locally. Only a sample of prompts is read by Claude, in your own session.
- The prompt coach runs locally with no network and no AI call. Its log (`~/.claude/prompt-coach/log.jsonl`) stores counts and flags, never prompt text.

## Release notes

**prompt-coach v1.0.3**
- The coach now uses each person's `focus` areas from their profile, so it is stricter only on that person's weak habits:
  - `done_check`: opening prompts up to 80 words (not 40) without "done when" are restated, and so are new instructions of 20+ words mid-session.
  - `context`: opening prompts that name no file, page or screen make Claude find the place first, and ask if more than one fits.
  - `bare_paste`: a paste with fewer than 10 words of instruction (not 6) counts as a bare paste.
  - `long_sessions`: the "start a new session" nudge comes at 20 prompts (not 30), then every 10.
  - `plan_mode`: multi-file tasks sent outside plan mode get a short plan and a "Go ahead?" before any edit, plus a Shift+Tab reminder.

**v1.0.0 (Dec 2026)**
- usage-report method v2: team working week and holidays; `/clear` and other housekeeping commands no longer count as prompts; IDE auto-context removed; new habits (done-check, bare pastes, verify rate, plan mode on big tasks, long sessions); Leverage v2 with Practices; fixed labels and a rubric with examples; progress vs last month and targets; Hindi/Gujarati reports; templates, the most expensive session, and ready-made files; team mode.
- prompt-coach v1.0.0: three layers (restate, stop bare pastes, `/prompt-coach:p`).
- **Not yet verified on a VS Code extension install.** The IDE-context removal is pattern-based. Ask one VS Code user (Avinash, Nakul or Savan) to try it first, and report anything odd.
- Method v2 numbers are not directly comparable with the v1 reports from Nov 2026. The dashboard shows v1 values only where they still mean the same thing.

## Layout

```
.claude-plugin/marketplace.json        marketplace "byte-builders-claude"
plugins/usage-report/                  skill + scripts (analyze, score, finalize, charts, build_report, team_summary)
plugins/prompt-coach/                  hook (scripts/coach.js), setup, /p skill, tests (node plugins/prompt-coach/tests/run.js)
```
