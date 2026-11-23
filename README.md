# Byte-Builders Claude Code toolkit

Two Claude Code plugins for the team, installed from this repo:

| Plugin | What it does | Commands |
|---|---|---|
| **usage-report** | Monthly usage and prompt-quality report in simple English (coach tips in Hindi, Gujarati or English), prompt templates, progress vs last month, and ready-made setup files | `/usage-report` · `/usage-report monthly 2026-12` |
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

   If `marketplace add` fails with "Could not read from remote repository", your SSH key isn't set up for GitHub. Run `gh auth login`, then set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` in your environment and try again. You also need access to this repo.
3. Keep 90 days of history, so monthly reports are complete. Add this to `~/.claude/settings.json`:
   ```json
   { "cleanupPeriodDays": 90 }
   ```
4. Restart Claude Code, then run `/prompt-coach:setup`.
5. **Connect your Google Drive folder** (once). A Google Drive folder with your name is shared with you.
   - Install [Google Drive for desktop](https://www.google.com/drive/download/) and sign in with your work account.
   - In drive.google.com > **Shared with me**, right-click your folder > **Organise > Add shortcut** > **My Drive**. A shared folder does not appear on your computer until you do this.
   - Wait until it shows in File Explorer, usually as `G:\My Drive\<YourName>`, then run in Claude Code:
     ```
     /usage-report share "G:/My Drive/<YourName>"
     ```

## Update (when a new version is announced)

```
claude plugin marketplace update byte-builders-claude
claude plugin update usage-report@byte-builders-claude
claude plugin update prompt-coach@byte-builders-claude
```

## Every month

Between the 1st and 5th of each month (Claude reminds you at the start of a session until it is done):
1. Run `/usage-report`. It reports on the previous calendar month (team settings: Mon–Sat, holidays, IST) and uploads **only** `metrics.json`, `scores.json`, `coach-draft.json` and the `.docx` to your Drive folder. If the upload fails, fix what it says and run `/usage-report upload`.
2. Open `suggested/` in `~/Documents/claude-usage-reports/<YYYY-MM>/`: a `CLAUDE.md` snippet, a permissions allowlist and draft slash commands made from your own work. Use what helps.
3. Your prompt coach does **not** change yet. Your report is reviewed first. Once it is approved, your coach updates at the start of a Claude Code session and tells you what changed.

## Layout

```
.claude-plugin/marketplace.json        marketplace "byte-builders-claude"
plugins/usage-report/                  skill + scripts (analyze, score, finalize, charts, build_report, team_summary)
plugins/prompt-coach/                  hook (scripts/coach.js), setup, /p skill, tests (node plugins/prompt-coach/tests/run.js)
```
