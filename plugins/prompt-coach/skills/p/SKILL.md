---
name: p
description: Turns a rough request (any language, Hindi/Gujarati/Hinglish welcome) into a clear structured prompt, shows it, and runs it only after the user confirms. Use when the user types /prompt-coach:p or /p followed by an idea.
argument-hint: "<your rough request, any language>"
---

# /p — improve my prompt, then run it

The user's rough request is: $ARGUMENTS

1. Read the request. If it points at the current work, also use the conversation, the open project and its CLAUDE.md. Look at the files it mentions (read only; change nothing yet).
2. Write an improved prompt in **simple English**, in this shape, in a fenced block:
   ```
   Goal: <one sentence: the end state>
   Context: <why, for whom, where in the code — file paths if known>
   Scope: <what to change> · Don't change: <what must stay>
   Steps: <only for multi-step work: 2-5 short steps, starting with "plan first" when it touches more than 3 files>
   Done when: <the test that passes, or what the screen shows, at which sizes>
   Reply with: <format of the answer, e.g. root cause in 2 lines + files changed>
   ```
   Keep every line short. Mark anything you guessed with "(?)".
3. Under it, explain in one or two lines **in the user's language** (from `~/.claude/prompt-coach/profile.json` → `language`; Hindi by default, Gujarati if "gu", simple English if "en"; technical words stay English) what you added and why it helps.
4. Ask with AskUserQuestion: **Run this** / **Edit first** / **Cancel**.
   - Run this → do the work exactly as the improved prompt says, including the Done-when check.
   - Edit first → ask what to change, show the new version, and ask again.
   - Cancel → stop.

Never run tools that change anything before the user picks "Run this".
