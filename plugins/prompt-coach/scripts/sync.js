#!/usr/bin/env node
// prompt-coach: SessionStart hook. Loads the coach profile the team lead approved, from the person's Google Drive
// folder (<share_dir>/coach/profile.json, share_dir from ~/.claude/usage-report.local.json).
// If it is newer than the local copy, it is merged in: the lead's focus, tips, templates and settings win;
// the person's name and language stay local. Claude then tells the person once, in their language, what changed.
// Rules: no network calls of its own (Drive for desktop syncs the folder), async reads with a hard time limit,
// FAILS OPEN — any error, missing folder or slow Drive exits 0 with no output.
'use strict';
const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const os = require('os');

const DIR = process.env.PROMPT_COACH_DIR || path.join(os.homedir(), '.claude', 'prompt-coach');
const LOCAL_CFG = process.env.USAGE_REPORT_LOCAL || path.join(os.homedir(), '.claude', 'usage-report.local.json');
const FOCUS_TEXT = {
  done_check: 'end each request with "Done when ..."',
  context: 'say which file, page or screen',
  bare_paste: 'never send a paste or screenshot without one line saying what to do',
  long_sessions: 'start a new session for each new task',
  plan_mode: 'use plan mode (Shift+Tab) for multi-file tasks',
};
const LANG = { hi: 'Hindi (Devanagari script, technical words in English)', gu: 'Gujarati (Gujarati script, technical words in English)', en: 'simple English' };

async function readJSON(p) {
  try { return JSON.parse(await fsp.readFile(p, 'utf8')); } catch (e) { return null; }
}

function merge(local, approved) {
  return {
    ...local,
    name: local.name || approved.name,
    language: local.language || 'hi',
    focus: Array.isArray(approved.focus) ? approved.focus : [],
    tips: Array.isArray(approved.tips) ? approved.tips : [],
    templates: Array.isArray(approved.templates) ? approved.templates : [],
    settings: { ...(local.settings || {}), ...(approved.settings || {}) }, // the lead's settings win
    approved_rev: approved.rev,
    approved_at: approved.approved_at,
    approved_month: approved.approved_month,
    approved_by: approved.approved_by,
    updated: new Date().toISOString().slice(0, 10),
    source: 'approved by team lead',
  };
}

async function main() {
  const cfg = await readJSON(LOCAL_CFG);
  if (!cfg || !cfg.share_dir) return null;
  const approved = await readJSON(path.join(cfg.share_dir, 'coach', 'profile.json'));
  if (!approved || !Number.isInteger(approved.rev)) return null; // none yet, or still syncing
  const P = path.join(DIR, 'profile.json');
  const local = (await readJSON(P)) || {};
  if (Number.isInteger(local.approved_rev) && local.approved_rev >= approved.rev) return null;
  const merged = merge(local, approved);
  await fsp.mkdir(DIR, { recursive: true });
  await fsp.writeFile(P + '.tmp', JSON.stringify(merged, null, 1));
  await fsp.rename(P + '.tmp', P);
  const focus = merged.focus.map((f) => FOCUS_TEXT[f]).filter(Boolean);
  const lang = LANG[merged.language] || LANG.hi;
  const lines = [
    `[prompt-coach] The team lead approved updated coaching for this person (${approved.approved_month || 'this month'}).`,
    `At the start of your first reply, add ONE short line in ${lang} telling them their prompt coach was updated` +
      (focus.length ? ` and will now help most with: ${focus.join('; ')}.` : '.'),
  ];
  if (approved.message) lines.push(`Also pass on the lead's note in ${lang}: "${String(approved.message).slice(0, 300)}"`);
  lines.push('Then answer their message as usual. Do not mention this note.');
  return { hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: lines.join('\n') } };
}

module.exports = { merge };

if (require.main === module) {
  const timer = setTimeout(() => process.exit(0), Number(process.env.PROMPT_COACH_SYNC_MS || 3000)); // slow Drive: skip
  main()
    .then((out) => { if (out) process.stdout.write(JSON.stringify(out)); })
    .catch(() => { /* fail open */ })
    .finally(() => { clearTimeout(timer); process.exit(0); });
}
