# claude-usage-report: install and use

A Claude Code skill that produces a personal Claude usage and prompt-quality report as a Word file.

## Install (once)

1. Unzip so this folder ends up at `~/.claude/skills/claude-usage-report/`. On Windows that is `%USERPROFILE%\.claude\skills\claude-usage-report\`. `SKILL.md` must sit directly inside that folder.
2. Make sure you have:
   - Python 3.10 or later with matplotlib (`pip install matplotlib`; on Windows also run `pip install tzdata`);
   - Node.js 18 or later.
3. Restart Claude Code. The skill appears as `/claude-usage-report`.

## Run

In Claude Code, from any folder, type `/claude-usage-report`.

Claude asks for your name, plan and price, and whether you have a claude.ai export. It then analyses your last 30 days of Claude Code sessions, which are already stored on your machine. The report is saved to:

`~/Documents/claude-usage-reports/<date>/claude-usage-report_<your-name>_<start>_to_<end>.docx`

## What to send back

Send **only** these three files:
- the `.docx`;
- `metrics.json`;
- `scores.json`.

The other files in that folder contain your raw prompts. They stay on your machine.

## Notes

- **History:** Claude Code keeps only 30 days of transcripts by default. To keep more history for future reports, add `"cleanupPeriodDays": 90` to `~/.claude/settings.json`.
- **What the analysis reads:** the transcripts in `~/.claude/projects`, read locally. The only data that goes to Claude is a sample of your prompts, for scoring in your own session.
