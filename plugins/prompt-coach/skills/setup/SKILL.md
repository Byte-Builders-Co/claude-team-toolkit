---
name: setup
description: Sets up or changes the prompt coach for this person (name, Hindi or Gujarati, block mode on/off), imports a profile from the team lead, or shows how often the coach helped. Use when the user types /prompt-coach:setup, or asks to turn the prompt coach on/off, change its language, or see its status.
argument-hint: "[status | import <file> | language hi|gu | block on|off|ask | disable | enable]"
---

# Prompt coach setup

`SCRIPTS` = this skill's base directory + `/../../scripts`. Run with `node`.

- **No arguments, first time** (no `~/.claude/prompt-coach/profile.json`): ask once, in one message, for the person's name and their explanation language (Hindi default, or Gujarati). Then run
  `node SCRIPTS/setup.js --name "<name>" --language hi|gu`
- **import <file>**: `node SCRIPTS/setup.js --import "<file>"` (a profile JSON the team lead sent).
- **status**: `node SCRIPTS/setup.js --status`. Report it in the person's language: how many prompts were checked, how many were restated, stopped or asked about, and the current settings.
- **language hi|gu**: `node SCRIPTS/setup.js --language <hi|gu>`
- **block on|off|ask**:
  - on → `--block block --days 21` stops bare pastes for 3 weeks
  - ask → `--block ask`: Claude asks instead of stopping
  - off → `--block off`
- **disable / enable**: `--disable` / `--enable`

After any change, show the saved settings in one short line in the person's language. Remind them that the monthly `/usage-report` run refreshes the tips and templates in the profile automatically.
