# Judging rubric (method v2)

Use this for every judged session, so different people's reports are scored the same way.

## How to read a sample block

```
=== S07 2026-11-04 cardeed-web prompts=14
OUTCOME: prompts=14 corrections=3 interrupts=2 rejections=1 limit_hits=0 files_edited=9 verify_runs=0 verified_after_last_edit=no plan_mode=no output_tokens=181000
OPEN: <first prompt, up to 1,500 characters>
  FU: <follow-up 1>  ... up to 4
```

- Score the **prompts**, but use the **OUTCOME** line as evidence. Many corrections or interrupts after a vague opener show that the opener was missing something. Say so in the readings ("this 6-word prompt led to 14 follow-ups").
- A short prompt that fully serves a simple task can score 4–5. Never reward length for its own sake.
- **Never penalise** spelling, grammar, or Hindi/Gujarati/Hinglish. "esko mobile pe bhi responsive karo, 375px pe check karo" has a clear target and a check, so it scores well. "nai yaar professional look" has neither, so it scores low. The reason is the missing target, not the language.
- IDE auto-attached context has already been removed. Judge only what the person wrote, plus the pasted material they chose to include.

## Dimensions (1–5), with anchor examples

**1. Goal clarity:** is the wanted end state clear?
- 1: "check this" · "fix it" · "still not work proper please work proper"
- 3: "the footer remove the logo and align address in one line" (the task is clear, the success criteria are not)
- 5: "Remove the logo from the footer and put the links and address in one row on desktop, stacked on mobile."

**2. Context:** does Claude know why, where, and what it's working with?
- 1: a bare pasted log or screenshot, nothing else
- 3: names the page or file but not why ("in BookingController fix the date")
- 5: purpose plus facts: "Front desk can't see tomorrow's check-ins because BookingController filters by created_at; it should use check_in_date."

**3. Specificity & constraints:** scope, must-haves, must-not-change.
- 1: "make it professional" · "proper and perfect"
- 3: "make it responsive, use theme colour"
- 5: "Only touch site-footer.tsx. Keep current colours and links. No new packages."

**4. Output specification ("done when"):** how will we know it worked, and in what form should the answer come?
- 1: nothing
- 3: implied ("so the test passes")
- 5: "Done when `npx playwright test booking.spec.ts` passes twice in a row; reply with the root cause in 2 lines and the files changed."

**5. Steering & follow-ups** (leave blank when there are no follow-ups):
- 1: repeats the same ask, "do continue", the same error pasted again with no new facts
- 3: some new information mixed with re-asks
- 5: each follow-up adds a new fact: what was seen, where, and what was expected. Numbered answers to Claude's questions ("1.yes 2.B") count as good steering.

**6. Technique & leverage:** uses the tools that make Claude reliable.
- 1: none
- 3: one useful technique (file pointer, screenshot plus a sentence, "ask me questions first")
- 5: plan mode or "plan first, wait for my OK" on big work, points at files, asks Claude to run tests or lint and report what it verified

## Fixed labels (score.py rejects anything else)

**use_case**, pick one:
`Feature build` · `Bug fix / debugging` · `UI / styling` · `Tests & QA` · `Refactor / cleanup` · `DevOps / config` · `Investigation / review` · `Docs / planning / research` · `Git & release` · `Other`

**complexity**, pick one:
- `Light`: a quick fix, a single question, one small UI tweak
- `Substantive`: a multi-step change in one area (a form, an endpoint and its test)
- `Advanced`: a multi-file feature, an audit, a refactor across modules, a test-suite or coverage drive, a production incident

## Calibration check before saving

Before writing judged_scores.csv, re-read your three highest and three lowest sessions against the anchors above. If a score doesn't match its anchor, fix it. Save in batches of about 15 rows.
