# Methodology

## Inputs

Some or all of these will be present. Inventory what is actually there and adapt to it.

- **A. Organisation data export** (ZIP/JSON): members' conversations with their messages, plus a users file. This is the main source for activity and prompt text.
- **B. Analytics API output** (JSON from `/v1/organizations/analytics/users`, Enterprise only): per-user `chat_metrics`, `cowork_metrics`, `claude_code_metrics`, `office_metrics`, `design_metrics`, `web_search_count` and `last_activity_date`. Daily files (one per date) give active days. A date-range rollup gives totals only.
- **C. Compliance API exports** (JSON, Enterprise only): chats and session transcripts (Cowork, Claude Code, Office add-ins). These are an extra or alternative source of prompt text.
- **D. Spend report CSV**: one row per user per model. Typical columns are User's email, Product, Model, total_requests, total_prompt_tokens, total_completion_tokens, total_net_spend_usd and total_gross_spend_usd.
- **E. Claude Code leaderboard CSV** ("Export all users"): PRs and lines of code per user.
- **F. Screenshots or notes from Organization settings > Usage**: month-to-date spend per member, spend limits, "Blocked by a spend limit" and members near their limit.
- **G. Team mapping CSV** (optional): email, name, team, role, seat type (Standard/Premium).
- **H. Claude Code OpenTelemetry logs** (optional): `claude_code.user_prompt` events with `user.email`.

## Step 1: Inventory

1. List each file with its type, size, date range, record count and key fields. Inspect the real schema before parsing.
2. Infer the plan and state the evidence:
   - If B or C is present, the plan is Enterprise.
   - If the spend report covers only a few users or small amounts, the plan is seat-based (Team or seat-based Enterprise). On these plans the spend report shows only usage above the seat allowance (usage credits / overage).
   - If the spend report covers nearly everyone, the plan is usage-based Enterprise, where spend equals all usage.
   - Otherwise, state your assumption.
3. Build one master user list keyed on lower-cased email. Map user IDs/UUIDs to emails via the users file. **Keep seat holders with zero activity**, because they matter most for licence decisions. Exclude only obvious test or service accounts, and list them.
4. Filter everything to the reporting period, converting timestamps to the chosen time zone.

## Step 2: Usage per user

Where the data can't support a metric, write N/A and explain why. Never estimate silently.

- **Activity:**
  - Active days: distinct dates with at least one prompt or session in any product.
  - Active-day rate = active days ÷ working days.
  - Weeks active, and last active date.
- **Volume:**
  - Prompts sent (user messages) and conversations or sessions, split by product (Chat, Cowork, Claude Code, Office, Design) where the data allows.
  - Prompts per active day.
  - Average user turns per conversation.
- **Breadth:**
  - Distinct capabilities used. Possible capabilities are projects, file uploads, artifacts, connectors/MCP, skills, web search, extended thinking, Cowork, Claude Code and Office add-ins.
  - Breadth count = number of capabilities used.
  - Count only capabilities you can detect in the data, and list which ones those were.
- **Claude Code** (if present):
  - Sessions, lines added/accepted, commits and PRs.
  - Accept rate = accepted ÷ (accepted + rejected) edit/write actions.
- **Tokens and spend:** from D, summed across models, plus each user's share of the org total.

## Step 3: Allowance status

Admins can't see per-person usage against the seat limit on seat-based plans. Use the strongest evidence available and record which evidence you used for each user. Assign the **first** status that applies:

1. **Dormant**: no activity in the period, or none in its final 21 days.
2. **Constrained**: evidence the user hit their limit. Any of these counts:
   - overage or usage-credit spend on a seat-based plan;
   - shown as blocked or near their limit in F;
   - on usage-based Enterprise, spend of at least 80% of their personal spend limit.
3. **High**: active-day rate ≥ 60%, or prompt volume in the top quartile of active users.
4. **Moderate**: active-day rate 25–59%.
5. **Low**: active-day rate < 25%.

Mark any status that rests only on activity as "proxy".

If a seat cost is given, show:
- seat cost per active day;
- the monthly cost of Dormant and Low seats.

Flag Constrained users as candidates for a Premium seat or usage credits. If seat type is known, flag Premium holders who are Dormant or Low as downgrade candidates.

## Step 4: Prompt quality

Run this step only if prompt text is available (A, C or H). Say which products the text covers.

**4a. Signals over all of each user's prompts** (compute with code):
- median prompt length in words;
- % of prompts with 30+ words;
- % of conversations with a file or attachment;
- % of prompts that specify an output format (table, bullets, JSON/CSV, word count, email, slides…);
- % of prompts that give context or purpose (audience, goal, background, "because", "for our…");
- correction rate = share of follow-ups that correct or re-ask ("no", "that's wrong", "not what I asked", "try again", "still not working", near-duplicate rephrasing);
- % of one-message conversations.

**4b. Judged sample:**
- **Sample size:** aim for about 300 judged conversations in total. Judge `floor(min(10, max(3, 300 ÷ active users)))` conversations per user.
- **Selection:** spread the sample evenly across the period and across products. Prefer substantive conversations and skip greetings and test messages.
- **What to read:** the opening prompt (first ~1,500 characters) and up to 4 of the user's follow-ups (first ~300 characters each).
- **Saving:** work in batches and **save scores to a CSV as you go**.
- **Users with fewer than 3 conversations:** score what exists and mark confidence "low".

Score each conversation from 1 to 5 on:

1. **Goal clarity.** 1: vague ("help with this"). 3: task clear, success criteria missing. 5: clear task and what "done" looks like.
2. **Context.** 1: none. 3: some background. 5: purpose, audience, key facts and source material given or attached.
3. **Specificity & constraints.** 1: open-ended. 3: some requirements. 5: scope, must-haves, tone, constraints and edge cases stated.
4. **Output specification.** 1: none. 3: implied. 5: explicit format, length and structure.
5. **Steering & iteration.** 1: repeated re-asking, frustration or abandonment. 3: some corrections. 5: short, specific follow-ups that build on the answer. Leave this dimension out for conversations with no follow-ups.
6. **Technique & leverage.** 1: none. 3: one useful technique. 5: examples, a step-by-step breakdown, files, projects, connectors, skills or web search, or (for agentic tasks) success criteria and a request to verify, wherever these would help.

Judge against what the task needed. A short prompt that fully serves a simple task can score 4–5. Never reward length for its own sake.

Also tag each conversation with:
- **Use case:** Coding & dev, Writing & comms, Data & analysis, Research, Marketing & product content, Customer service, Operations & admin, Learning & how-to, or Other.
- **Complexity:** Light (quick lookup or rewrite), Substantive (a multi-part work product) or Advanced (multi-step analysis, a build or an agentic workflow).

**4c. Score:** prompt-quality score = mean of the six dimension means (1–5), converted to 0–100 as `(score − 1) ÷ 4 × 100`. Report confidence as the number of conversations judged (n).

**4d. Data-handling check** (counts only): count prompts per user that appear to contain:
- passwords, API keys or tokens;
- payment-card-like numbers;
- bulk customer personal data (lists of names with emails, phone numbers or addresses).

Never reproduce the content. Treat these counts as a coaching point, not a breach finding.

## Step 5: KPIs

**Claude Leverage Score (0–100)** per user:

| Component | Points | Formula |
|---|---|---|
| Engagement | 30 | `30 × min(1, active-day rate ÷ 0.60)` |
| Depth | 15 | `15 × percentile rank (0–1) of prompts per working day among active users` |
| Breadth | 15 | `15 × min(1, breadth ÷ min(5, number of detectable capabilities))` |
| Prompt quality | 30 | `30 × prompt-quality score ÷ 100` |
| Outcomes | 10 | `10 × mean of available outcome percentiles among active users` |

The outcome percentiles are:
- artifacts/files created;
- 1 − correction rate;
- lines accepted and PRs, only for users with at least one Claude Code session.

If a component is N/A for a user, rescale that user's remaining weights to total 100, mark the score "partial" and say what was missing. Users with no activity score 0.

**Tiers:**

| Score | Tier |
|---|---|
| 80–100 | Champion |
| 60–79 | Proficient |
| 40–59 | Developing |
| 20–39 | Low adoption |
| 0–19 | Inactive (seat review) |

- Dormant users go to Inactive (seat review) whatever their score. Show the score for reference.
- Champion also requires a prompt-quality score of at least 60 when quality was scored. Otherwise cap the user at Proficient.

**Usage × quality quadrant.** High usage = allowance status Constrained or High. Good quality = prompt-quality score of 60 or more.

| | Good quality | Weak quality |
|---|---|---|
| **High usage** | Power user: involve as a mentor or case study | Busy but inefficient: prompt coaching saves time and allowance |
| **Light/moderate usage** | Untapped: show them more use cases | Needs onboarding (seat review if Dormant) |

If quality is N/A, use "Unscored" for high-usage users and Needs onboarding for everyone else.

**Org-level KPIs**, each against a suggested starting target (adjustable):

| KPI | Target |
|---|---|
| Seat activation: share of seats with ≥ 1 active day | 85% or more |
| Habitual use: share of seats with an active-day rate of 40% or more | 50% or more |
| Median Leverage Score | 55 or more |
| Median prompt-quality score | 60 or more |
| Dormant seats | 10% or less |
| Constrained users | No target; a high share means limits are holding people back |

## Step 6: Report sections

1. **Executive summary** (one page max):
   - seats vs active users;
   - org-level KPIs against targets;
   - tier and quadrant counts;
   - the 3–5 most important findings;
   - recommended actions (seat changes, training themes, champions to involve).
2. **Adoption and allowance:**
   - org-level table with short commentary;
   - idle-seat cost, if a seat cost was given;
   - Constrained users and what to do about them.
3. **Per-user scorecard table:** Name, Team, Products used, Active days (rate), Prompts, Allowance status, Prompt quality (0–100, n judged), Leverage Score, Tier, Quadrant. Sort by Leverage Score, highest first.
4. **Prompt quality across the org:**
   - dimension averages;
   - the two weakest dimensions, each with a short "what good looks like" example;
   - use-case and complexity mix (by team if G is provided).
5. **Coaching notes for every active user:**
   - one strength;
   - two specific improvements tied to their weakest dimensions;
   - a before/after rewrite of one of their own prompts (paraphrased and redacted, 40 words max each).
6. **Data-handling observations** (counts only).
7. **Methodology, data sources and gaps:**
   - files used and plan inference;
   - formulas and thresholds;
   - what's measured vs proxy;
   - sample sizes and limitations.

With more than 25 users, move the full scorecard and coaching notes to an appendix and also save the scorecard as a CSV.

## Step 7: Final checks

- **Fairness:**
  - flag low-confidence scores;
  - compare teams only when they have at least 5 people;
  - don't penalise short prompts that fully serve simple tasks.
- **Before finishing, verify that:**
  - user counts agree across sections;
  - Leverage weights total 100;
  - every active user has a score and a coaching note;
  - no raw personal data is in the report.
