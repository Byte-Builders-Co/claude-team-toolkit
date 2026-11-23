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
4. Restart Claude Code, then run `/prompt-coach:setup`.
5. **Connect your Google Drive folder** (once). The lead shares a folder with your name with you.
   - Install [Google Drive for desktop](https://www.google.com/drive/download/) and sign in with your work account.
   - In drive.google.com > **Shared with me**, right-click your folder > **Organise > Add shortcut** > **My Drive**. A shared folder does not appear on your computer until you do this.
   - Wait until it shows in File Explorer, usually as `G:\My Drive\<YourName>`, then run in Claude Code:
     ```
     /usage-report share "G:/My Drive/<YourName>"
     ```

## Update (when the lead announces a new version)

```
claude plugin marketplace update byte-builders-claude
claude plugin update usage-report@byte-builders-claude
claude plugin update prompt-coach@byte-builders-claude
```

## Every month

**Everyone (1st–5th of the month).** Claude reminds you at the start of a session until it is done.
1. Run `/usage-report`. It reports on the previous calendar month (team settings: Mon–Sat, holidays, IST) and uploads **only** `metrics.json`, `scores.json`, `coach-draft.json` and the `.docx` to your Drive folder. If the upload fails, fix what it says and run `/usage-report upload`.
2. Open `suggested/` in `~/Documents/claude-usage-reports/<YYYY-MM>/`: a `CLAUDE.md` snippet, a permissions allowlist and draft slash commands made from your own work. Use what helps.
3. Your prompt coach does **not** change yet. The lead reviews your report first. When they approve, your coach updates at the start of a Claude Code session and tells you what changed.

`prompts.csv`, `sample.txt`, `narrative.json` and `suggested/` stay on your computer. They contain your raw prompts.

**The lead (after the 5th).**
1. `/usage-report team` reads everyone's files from Drive, says who is missing, updates the history, refreshes the team dashboard, and writes `review.md`: per person, what improved, what to work on next, and the proposed coach changes.
2. Read the summary Claude shows, then approve or change it in plain words ("approve all, but keep Rushil on block mode").
3. `/usage-report approve` releases the approved coach profiles to each person's Drive folder.

## For the lead

**Google Drive setup (once).**
1. In Google Drive, create `Claude Reports` with a sub-folder per person (names as in `team-config.json` > `members`) and `_team`.
2. Share **each person's sub-folder only** with that person, as Editor. Do not share `Claude Reports` itself or `_team`: each person must see only their own files.
3. Make a sub-folder for yourself too, and do install step 5 yourself: your own report and coach go through the same review.
4. Copy the existing `history.json` and `kpi_history.csv` into `_team/`, so the dashboard keeps earlier months.
5. Tell everyone to do install step 5.

**Other settings.**
- Add holidays to `team-config.json` before the 1st, commit, and ask everyone to update.
- Coach settings per person (block mode, focus areas) are part of the monthly approval. Ask for changes during `/usage-report team`, for example "Rushil block mode off".

## Privacy

- The report reads `~/.claude/projects` locally. Only a sample of prompts is read by Claude, in your own session.
- The prompt coach runs locally with no network and no AI call. Its log (`~/.claude/prompt-coach/log.jsonl`) stores counts and flags, never prompt text. Only those counts go into `coach-draft.json`.
- Drive gets only the four files listed above. Each person's Drive folder is shared with that person and the lead, nobody else.

## Release notes

**prompt-coach v1.1.1**
- English is now a coach language (`/prompt-coach:setup language en`), next to Hindi and Gujarati.

**usage-report v1.1.1**
- Team mode stops instead of starting a new history when `_team/history.json` is missing (it would drop earlier months from the dashboard).

**usage-report v1.1.0 / prompt-coach v1.1.0: monthly loop through Google Drive, with lead approval**
- The report uploads its shareable files to the person's Drive folder (`/usage-report share`, `/usage-report upload`). Raw prompts never leave the computer.
- The report no longer changes the prompt coach directly. It writes `coach-draft.json`; the lead reviews it (`/usage-report team`) and approves it (`/usage-report approve`). The coach loads the approved profile at the next session start (SessionStart hook) and says once what changed. The lead's settings win; each person's language stays.
- Reminder on the 1st–5th of the month until the report is in Drive.
- `/prompt-coach:setup import` now lets the lead's settings win over local ones.
- Team mode lists who has not submitted, refreshes the dashboard and writes `review.md` and `proposal.json`. The old `Reports/<YYYY-MM>/<Name>/` layout still works with `--month-dir`.

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
