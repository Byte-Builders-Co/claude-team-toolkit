#!/usr/bin/env node
// prompt-coach setup and status.
// node setup.js --name "Avinash" [--language hi|gu] [--block block|ask|off] [--days 21] [--enable|--disable]
// node setup.js --import path/to/profile.json      (profile prepared by the team lead)
// node setup.js --status                           (last 30 days, from log.jsonl; no prompt text is stored)
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

const DIR = process.env.PROMPT_COACH_DIR || path.join(os.homedir(), '.claude', 'prompt-coach');
const P = path.join(DIR, 'profile.json');
const args = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : undefined; };
const has = (k) => args.includes(`--${k}`);
const read = (p, f) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return f; } };
const addDays = (d) => new Date(Date.now() + d * 864e5).toISOString().slice(0, 10);

if (has('status')) {
  const prof = read(P, null);
  const since = Date.now() - 30 * 864e5;
  const counts = {};
  let total = 0;
  try {
    for (const line of fs.readFileSync(path.join(DIR, 'log.jsonl'), 'utf8').split('\n')) {
      if (!line) continue;
      try {
        const r = JSON.parse(line);
        if (Date.parse(r.ts) < since) continue;
        total += 1;
        counts[r.action] = (counts[r.action] || 0) + 1;
      } catch (e) { /* skip */ }
    }
  } catch (e) { /* no log yet */ }
  console.log(JSON.stringify({ profile: prof ? { name: prof.name, language: prof.language, focus: prof.focus, settings: prof.settings, updated: prof.updated } : null, last_30_days: { prompts_checked: total, ...counts } }, null, 1));
  process.exit(0);
}

let prof = read(P, {});
if (opt('import')) {
  const imp = read(opt('import'), null);
  if (!imp) { console.error(`Cannot read ${opt('import')}`); process.exit(1); }
  // The lead's file wins on focus, tips, templates and settings; this person's name and language stay.
  prof = { ...prof, ...imp, name: prof.name || imp.name, language: prof.language || imp.language, settings: { ...(prof.settings || {}), ...(imp.settings || {}) } };
}
prof.version = 1;
if (opt('name')) prof.name = opt('name');
if (opt('language')) {
  if (!['hi', 'gu'].includes(opt('language'))) { console.error('--language must be hi or gu'); process.exit(1); }
  prof.language = opt('language');
}
prof.language = prof.language || 'hi';
prof.settings = { enabled: true, block_mode: 'block', min_words: 12, long_session_prompts: 30, tip_every: 3, ...(prof.settings || {}) };
if (!prof.settings.block_until) prof.settings.block_until = addDays(Number(opt('days') || 21));
if (opt('block')) {
  if (!['block', 'ask', 'off'].includes(opt('block'))) { console.error('--block must be block, ask or off'); process.exit(1); }
  prof.settings.block_mode = opt('block');
  if (opt('block') === 'block') prof.settings.block_until = addDays(Number(opt('days') || 21));
}
if (has('disable')) prof.settings.enabled = false;
if (has('enable')) prof.settings.enabled = true;
prof.focus = prof.focus || [];
prof.tips = prof.tips || [];
prof.templates = prof.templates || [];
prof.updated = new Date().toISOString().slice(0, 10);
fs.mkdirSync(DIR, { recursive: true });
fs.writeFileSync(P, JSON.stringify(prof, null, 1));
console.log(`Saved ${P}`);
console.log(JSON.stringify({ name: prof.name, language: prof.language, settings: prof.settings, tips: prof.tips.length, templates: prof.templates.length }, null, 1));
