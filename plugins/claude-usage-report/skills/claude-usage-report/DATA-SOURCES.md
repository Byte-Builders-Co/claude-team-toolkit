# Where to get the data

## Personal mode

| | Source | Where | What it adds |
|---|---|---|---|
| P1 | Claude Code transcripts | Already on disk: `~/.claude/projects/**/*.jsonl`. Nothing to download. | Claude Code prompts, sessions, tools, commits, limit hits and tokens. Only the last `cleanupPeriodDays` are kept (default 30). Raise that setting in `~/.claude/settings.json` to keep more history for future reports. |
| P2 | claude.ai personal export | claude.ai → Settings → Privacy → Export data. The link is emailed. | Chat conversations from web, desktop and mobile, plus projects, files and artifacts |
| P3 | Plan and price, and optional Usage screenshots | You know your plan. Screenshots come from claude.ai → Settings → Usage. | Plan-fit verdict and cost per active day |

## Organisation mode

| | File | Plan | Who can pull it | Where | What it adds |
|---|---|---|---|---|---|
| A | Organisation data export | Team & Enterprise | Primary Owner only | Organization settings > Data and privacy > Export data (the link is emailed and expires after 24h) | Activity per person plus the actual prompts. **Minimum needed.** |
| D | Spend report CSV | Team & Enterprise | Owner / Primary Owner | Settings > Analytics > Export spend report (Custom dates) | Who went past their seat allowance. On seat-based plans it covers only spend above the allowance, and only if usage credits are on. On usage-based Enterprise it covers everyone's full usage. |
| E | Claude Code leaderboard CSV | Team & Enterprise | Owner / Admin | claude.ai/analytics/claude-code > Leaderboard > Export all users (PR and lines-of-code data needs the GitHub integration) | Claude Code outcomes |
| F | Usage page screenshot | Team & Enterprise | Owner / Primary Owner | Organization settings > Usage ("Spend limits by user", "Blocked by a spend limit") | Who is blocked or near a limit |
| G | Team mapping CSV | Any | You | Make it yourself: email, name, team, role, seat type | Team comparisons and seat recommendations |
| B | Analytics API JSON | Enterprise only | Primary Owner creates a `read:analytics` key | `GET https://api.anthropic.com/v1/organizations/analytics/users?date=YYYY-MM-DD` (one call per day of the period) | Per-user metrics for Chat, Cowork, Claude Code, Office add-ins and Design |
| C | Compliance API export | Enterprise only | Compliance access key (`read:compliance_user_data`) | `/v1/compliance/apps/chats` (+ `/messages`) and `/v1/compliance/apps/sessions/...` | Chat text plus Cowork and Claude Code session transcripts |
| H | Claude Code OpenTelemetry logs | Any (optional) | Whoever runs your telemetry | Turn on Claude Code telemetry with `OTEL_LOG_USER_PROMPTS=1` (via managed settings) and export the `claude_code.user_prompt` events | Claude Code prompts on Team, since the org export doesn't include them |

## Good to know

- On Team and seat-based Enterprise, Anthropic doesn't show admins each person's usage against their seat limit. The report therefore combines overage spend (proof that someone hit the cap) with activity, and labels the activity-based statuses as proxies.
- Docs:
  - [Usage analytics](https://support.claude.com/en/articles/12883420-view-usage-analytics-for-team-and-enterprise-plans)
  - [Org data export](https://support.claude.com/en/articles/13346720-export-your-organization-s-data)
  - [Usage credits & limits](https://support.claude.com/en/articles/12005970-extra-usage-for-team-and-seat-based-enterprise-plans)
  - [Analytics API](https://platform.claude.com/docs/en/manage-claude/analytics-api)
  - [Compliance API](https://platform.claude.com/docs/en/manage-claude/compliance-content-data)
  - [Claude Code analytics](https://code.claude.com/docs/en/analytics)
  - [Claude Code telemetry](https://code.claude.com/docs/en/monitoring-usage)
