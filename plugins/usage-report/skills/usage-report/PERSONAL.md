# Personal methodology

Analyse one person's own Claude usage. There are no other users to compare with, so every score uses **absolute benchmarks** and **trends over time** instead of percentiles.

## Inputs

- **P1. Claude Code transcripts (always available locally):** `~/.claude/projects/<project-slug>/*.jsonl`, one JSON event per line, one file per session.
  - **Retention:** Claude Code deletes transcripts after `cleanupPeriodDays` (default 30). Report the oldest transcript date. If the period starts before it, note that the Claude Code data is truncated.
  - **Real prompts:** a real user prompt is a `user` event whose content is the person's own text. Exclude:
    - `tool_result` blocks;
    - meta, system and command-output messages, such as `<command-name>`, `<local-command-stdout>`, `<system-reminder>`-only content and hook output;
    - interrupt markers;
    - sidechain/subagent events (`isSidechain: true`);
    - (v2) IDE auto-attached context (`<ide_…>` blocks), interrupt markers (`[Request interrupted…]`, counted as interrupts), and housekeeping slash commands (`/clear`, `/compact`, `/login`, `/restart` …, counted separately).
  - **Inspect the real keys before trusting any of these.**
  - **Field notes (Claude Code v2.x, verified Nov 2026):**
    - Also exclude `isCompactSummary: true`, `turnOrigin: "task_notification"` and texts starting "Below is a conversation log".
    - `promptSource` is `typed`, `suggestion_accepted`, `queued` or `sdk`.
    - Limit hits are `assistant` events with `quotaLimits.status == "rejected"` (`rateLimitType` gives `five_hour` or weekly).
    - User rejections are `user` events with `toolDenialKind == "user-rejected"`. Other kinds (`permission-rule`, `automode-blocked`) are hook or classifier blocks. Report those as friction, not as rejections.
    - `pr-link` events give PR URLs. `cost-state` gives `totalLinesAdded` / `totalLinesRemoved` per session.
    - Deduplicate `message.usage` by `message.id`.
  - **Script hygiene:**
    - Never name a script after a stdlib module (`inspect.py` broke `zoneinfo`).
    - `python -I` hides user-site `tzdata` on Windows. Run without `-I` from a folder that holds only your own scripts.
    - Every new file may trip a write-gate hook. Use few script files.
- **P2. claude.ai personal export (optional):** a ZIP from Settings → Privacy → Export data. It usually contains `conversations.json`, `projects.json` and `users.json`. Covers Chat only (web, desktop and mobile). Human messages are the prompts. Detect attachments/files, artifacts and projects where the schema allows.
- **P3. Plan and price (optional, from the user):** Free, Pro, Max 5x or Max 20x, and the monthly price. If the user gives Settings → Usage screenshots, use them as evidence for allowance.

## Step 1: Inventory

1. List each source with its type, size, record and session count, and date range. Print the schemas before parsing anything.
2. Set the period and the time zone. Filter everything to the period.
3. State which products each source covers, for example "Chat from export, Claude Code from transcripts".
4. Show a short inventory, then carry on without waiting.

## Step 2: Usage

Where the data can't support a metric, write N/A.

- **Activity:**
  - Active days: distinct dates with at least one real prompt in any product.
  - Active-day rate = active days on working days ÷ working days.
  - Count weekend active days separately.
  - Longest streak of consecutive active days.
- **Volume:**
  - Prompts and conversations/sessions per product.
  - Prompts per active day.
  - Average prompts per conversation or session.
  - Hour-of-day profile.
- **Trend:** prompts and active days per week, plus the change between the first and second half of the period.
- **Breadth:** count the capabilities you can detect and list them. Examples:
  - Chat: projects, file uploads, artifacts, web search, extended thinking.
  - Claude Code: MCP tools, skills/slash commands, subagents (Task/Agent tool), plan mode, web fetch/search, hooks.
- **Claude Code** (from the transcripts):
  - sessions, tool calls by type, files edited;
  - git commits made by Claude;
  - edit rejection rate = edit/write calls the user rejected ÷ all edit/write calls;
  - token totals from `message.usage` (input, output and cache tokens), shown as tokens only. Don't calculate a cost.

## Step 3: Plan fit

Collect this evidence:
- **Limit hits:** count the days with a usage-limit message in the transcripts ("usage limit reached", "limit will reset", "5-hour limit", "weekly limit") and in any screenshots.
- **Engagement:** the active-day rate.
- **Cost per active day:** monthly price ÷ active days, prorated to the period, if a price is known.

Give the **first** verdict that applies:
1. **Constrained**: a limit was hit on 3 or more days, or in more than 10% of active days. Suggest a higher tier (Pro → Max 5x → Max 20x), or changes in habits that use less allowance, such as shorter context and fewer re-asks.
2. **Well matched**: active-day rate is 40% or more, and limits were hit rarely or never.
3. **Under-used**: active-day rate is below 40% and limits were never hit. On Max, suggest a lower tier. On Pro, suggest building more of a habit.

Label any verdict without limit evidence as "proxy".

## Step 4: Prompt quality

**4a. Signals over all prompts, per product:**
- median length in words;
- % of prompts with 30+ words;
- % of conversations with a file, attachment or @-file reference;
- % of prompts that specify an output format;
- % of prompts that give context or purpose;
- correction rate = share of follow-ups that correct or re-ask ("no", "that's wrong", "not what I asked", "try again", "still not working", near-duplicate rephrasing);
- % of one-message conversations.

**4b. Judged sample:**
- **Size:** 40–60 conversations or sessions, or all of them if there are fewer.
- **Selection:** stratify across weeks and products, in proportion to volume, with at least 10 per product when possible. Skip greetings and tests.
- **What to read:** the opening prompt (first ~1,500 characters) and up to 4 follow-ups (first ~300 characters each).
- **Saving:** save scores to a CSV in batches.

Score each conversation from 1 to 5 on these dimensions, using the anchor examples, the OUTCOME evidence and the fixed labels in [RUBRIC.md](RUBRIC.md):
1. Goal clarity
2. Context
3. Specificity & constraints
4. Output specification
5. Steering & iteration (leave it out when there are no follow-ups)
6. Technique & leverage (for Claude Code sessions, success criteria, a request to verify or test, plan mode and pointing at files all count)

Also tag each conversation with a use case and a complexity. Judge against what the task needed, and never reward length for its own sake.

**4c. Score:** prompt-quality score = mean of the dimension means, converted to 0–100 as `(score − 1) ÷ 4 × 100`. Give it per product and overall. Compare the first and second half of the period to show the trend.

**4d. Data handling:** count prompts that appear to contain passwords, API keys or tokens, card numbers, or third-party personal data. Give counts plus the date and product of each, but never the content. Pasted `.env` values and production credentials in Claude Code prompts are the usual culprits.

## Step 5: Personal Leverage Score (0–100)

| Component | Points | Formula (the benchmarks are adjustable; list them in the report) |
|---|---|---|
| Engagement | 20 | `20 × min(1, active-day rate ÷ 0.70)` (working days from team-config.json, holidays removed) |
| Depth | 10 | `10 × min(1, prompts per working day ÷ 20)` |
| Breadth | 10 | `10 × min(1, breadth ÷ min(6, detectable capabilities))` |
| Prompt quality | 30 | `30 × prompt-quality score ÷ 100` |
| Practices | 20 | `20 × mean of min(1, done-check share of openers ÷ 0.40), min(1, verify rate ÷ 0.60), min(1, plan-on-big rate ÷ 0.50), 1 − min(1, share of prompts in 30+ prompt sessions ÷ 0.50)`; leave out parts that can't be measured |
| Outcomes | 10 | `10 × mean of (1 − correction rate)`, plus `(1 − edit rejection rate)` if Claude Code was used |

Method v2 (Dec 2026) moved 35 points from engagement, depth and breadth, which every team member maxed out, into Practices. Tiers therefore shift; don't compare a v2 Leverage Score with a v1 one.

If a component is N/A, rescale the remaining weights to 100 and mark the score "partial".

**Tiers:**

| Score | Tier |
|---|---|
| 80–100 | Champion (also requires prompt quality of at least 60) |
| 60–79 | Proficient |
| 40–59 | Developing |
| 20–39 | Light user |
| 0–19 | Barely used |

Also give the score for the first and the second half of the period, so the user can see the trend.

## Step 6: Report sections

1. **Summary** (half a page):
   - Leverage Score and tier;
   - plan-fit verdict;
   - the 3 biggest wins and the 3 biggest opportunities.
2. **Usage and plan fit:**
   - activity table;
   - weekly trend chart;
   - hour-of-day profile;
   - product split;
   - limit hits;
   - cost per active day.
3. **Capabilities:** which capabilities were used, and 2–3 unused ones that would suit the user's actual use-case mix.
4. **Prompt quality:**
   - dimension scores per product;
   - signals table;
   - use-case and complexity mix;
   - trend.
5. **Coaching:**
   - the two weakest dimensions, each with "what good looks like";
   - 3–5 before/after rewrites of the user's own prompts (redacted, 60 words max each);
   - a 5-item habit checklist.
6. **Data-handling observations** (counts only).
7. **Methodology and gaps:** sources, coverage dates, transcript truncation, formulas and benchmarks, sample size, and which results are proxies.

## Step 7: Final checks

- Totals agree across sections.
- The Leverage weights total 100.
- No secrets or third-party personal data appear in the report.
- Every N/A has a reason.
