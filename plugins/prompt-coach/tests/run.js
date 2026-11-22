#!/usr/bin/env node
// Fixture tests for coach.js. Run: node plugins/prompt-coach/tests/run.js
// Uses a temporary PROMPT_COACH_DIR, so the real profile and log are never touched.
'use strict';
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const COACH = path.join(__dirname, '..', 'scripts', 'coach.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'coach-test-'));
const future = new Date(Date.now() + 10 * 864e5).toISOString().slice(0, 10);
fs.writeFileSync(path.join(tmp, 'profile.json'), JSON.stringify({
  name: 'Test', language: 'hi', tips: ['अंत में लिखें: Done when ...'],
  templates: [{ task: 'UI change', template: 'In ___, change ___ to ___. Done when it looks right at 375px and 1280px.' }],
  settings: { block_mode: 'block', block_until: future, tip_every: 1 },
}));

const LOG = 'Error: SQLSTATE[42S22]: Column not found\n  at BookingController.php:120\n  at Router.php:44\n  at Kernel.php:12\n  exit code 1';
const cases = [
  ['bare paste (block)', { prompt: LOG, session_id: 's1' }, 'block'],
  ['bare paste in paste tags (block)', { prompt: `<pasted_content id="1">\n${LOG}\n</pasted_content id="1">`, session_id: 's2' }, 'block'],
  ['image only (ask)', { prompt: '[Image #1]', session_id: 's3' }, 'ask'],
  ['Hinglish one-liner (coach)', { prompt: 'nai yaar professional look', session_id: 's4' }, 'coach'],
  ['vague English (coach)', { prompt: 'check this and fix', session_id: 's5' }, 'coach'],
  ['good prompt (none)', { prompt: 'In site-footer.tsx remove the logo and put links and address in one row on desktop, stacked on mobile. Keep the colours. Done when it looks right at 375px and 1280px.', session_id: 's6' }, 'none'],
  ['slash command (skip)', { prompt: '/clear', session_id: 's7' }, 'skip-command'],
  ['IDE-wrapped short prompt (coach)', { prompt: '<ide_opened_file>The user opened the file c:\\app\\Footer.tsx in the IDE. This may or may not be related.</ide_opened_file>\nfix this', session_id: 's8' }, 'coach'],
  ['Hinglish with done-check (none)', { prompt: 'checkout page pe payment ke baad order status Paid hona chahiye, abhi Pending dikh raha hai. OrderController check karo. Done when the order test passes.', session_id: 's9' }, 'none'],
];

let fail = 0;
for (const [name, input, expected] of cases) {
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [COACH], { input: JSON.stringify(input), env: { ...process.env, PROMPT_COACH_DIR: tmp }, encoding: 'utf8' });
  const ms = Date.now() - t0;
  let out = null;
  try { out = r.stdout ? JSON.parse(r.stdout) : null; } catch (e) { out = 'INVALID JSON'; }
  const got = out === null ? 'none' : out === 'INVALID JSON' ? 'invalid' : out.decision === 'block' ? 'block'
    : /AskUserQuestion with 2-4 options, such as/.test(out.hookSpecificOutput.additionalContext) ? 'ask' : 'coach';
  const log = fs.readFileSync(path.join(tmp, 'log.jsonl'), 'utf8').trim().split('\n').pop();
  const action = JSON.parse(log).action;
  const ok = (expected === 'skip-command' ? action === 'skip-command' && got === 'none' : got === expected) && r.status === 0;
  if (!ok) fail += 1;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name.padEnd(36)} expected=${expected.padEnd(12)} got=${got.padEnd(6)} exit=${r.status} ${ms}ms`);
}

// Follow-up answer after Claude asked a question: must not coach.
const tr = path.join(tmp, 't.jsonl');
fs.writeFileSync(tr, JSON.stringify({ type: 'assistant', message: { content: [{ type: 'text', text: 'Should I also update the tests?' }] } }) + '\n');
fs.writeFileSync(path.join(tmp, 'state', 's10.json'), JSON.stringify({ count: 3, flagged: 0, tipsShown: 0 }));
const r2 = spawnSync(process.execPath, [COACH], { input: JSON.stringify({ prompt: 'haan karo', session_id: 's10', transcript_path: tr }), env: { ...process.env, PROMPT_COACH_DIR: tmp }, encoding: 'utf8' });
const okAns = r2.stdout === '' && r2.status === 0;
if (!okAns) fail += 1;
console.log(`${okAns ? 'PASS' : 'FAIL'}  answer to Claude's question (none)`);

// Broken input: must exit 0 with no output.
const r3 = spawnSync(process.execPath, [COACH], { input: 'not json', env: { ...process.env, PROMPT_COACH_DIR: tmp }, encoding: 'utf8' });
const okBad = r3.stdout === '' && r3.status === 0;
if (!okBad) fail += 1;
console.log(`${okBad ? 'PASS' : 'FAIL'}  invalid stdin fails open`);

// Log must never contain prompt text.
const logText = fs.readFileSync(path.join(tmp, 'log.jsonl'), 'utf8');
const okPriv = !/SQLSTATE|professional|footer|checkout/i.test(logText);
if (!okPriv) fail += 1;
console.log(`${okPriv ? 'PASS' : 'FAIL'}  log has no prompt text`);

// ---- Focus areas (1.0.3): the same prompt is coached only for the person whose report flagged that habit. ----
function runWith(profile, input) {
  fs.writeFileSync(path.join(tmp, 'profile.json'), JSON.stringify(profile));
  const r = spawnSync(process.execPath, [COACH], { input: JSON.stringify(input), env: { ...process.env, PROMPT_COACH_DIR: tmp }, encoding: 'utf8' });
  const out = r.stdout ? JSON.parse(r.stdout) : null;
  return out === null ? 'none' : out.decision === 'block' ? 'block' : out.hookSpecificOutput.additionalContext;
}
const base = { language: 'hi', settings: { block_mode: 'block', block_until: future, tip_every: 1 } };
const long45 = 'Add a dark mode option to the settings page so users can switch between light and dark themes, remember the choice per user in the database, and update the header, sidebar, tables and all form inputs use the right colours in both themes';
const noWhere = 'Make the totals match the invoice amounts exactly. Done when the totals test passes.';
const big = 'Refactor the booking module so every controller uses the new pricing service. Done when all booking tests pass.';
const paste7 = `look at this one please thanks\n${LOG}`;
let sid = 100;
const focusCases = [
  ['long opener, no focus (none)', base, { prompt: long45 }, (g) => g === 'none'],
  ['long opener, done_check focus (coach)', { ...base, focus: ['done_check'] }, { prompt: long45 }, (g) => /Restated/.test(g)],
  ['no file/page, no focus (none)', base, { prompt: noWhere }, (g) => g === 'none'],
  ['no file/page, context focus (asks where)', { ...base, focus: ['context'] }, { prompt: noWhere }, (g) => /which file, page or screen/.test(g)],
  ['multi-file task, no focus (none)', base, { prompt: big }, (g) => g === 'none'],
  ['multi-file task, plan_mode focus (plan first)', { ...base, focus: ['plan_mode'] }, { prompt: big }, (g) => /numbered plan/.test(g) && /Shift\+Tab/.test(g)],
  ['multi-file task, already in plan mode (none)', { ...base, focus: ['plan_mode'] }, { prompt: big, permission_mode: 'plan' }, (g) => g === 'none'],
  ['paste + 5 words, no focus (coach, not block)', base, { prompt: paste7 }, (g) => g !== 'block'],
  ['paste + 5 words, bare_paste focus (block)', { ...base, focus: ['bare_paste'] }, { prompt: paste7 }, (g) => g === 'block'],
  ['unknown focus value is ignored', { ...base, focus: ['nonsense', 42] }, { prompt: noWhere }, (g) => g === 'none'],
];
for (const [name, profile, input, check] of focusCases) {
  const got = runWith(profile, { ...input, session_id: `f${sid++}` });
  const ok = check(got);
  if (!ok) fail += 1;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : '  got: ' + String(got).slice(0, 120)}`);
}
// long_sessions focus: nudge at prompt 20 instead of 30.
for (const [name, profile, expectNudge] of [['prompt 20, no focus (no nudge)', base, false], ['prompt 20, long_sessions focus (nudge)', { ...base, focus: ['long_sessions'] }, true]]) {
  const s = `L${sid++}`;
  fs.writeFileSync(path.join(tmp, 'state', `${s}.json`), JSON.stringify({ count: 19, flagged: 0, tipsShown: 0 }));
  const got = runWith(profile, { prompt: 'In site-footer.tsx make the links bold. Done when it looks right at 375px.', session_id: s });
  const ok = /session now has 20 prompts/.test(got) === expectNudge;
  if (!ok) fail += 1;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
}

fs.rmSync(tmp, { recursive: true, force: true });
console.log(fail ? `\n${fail} failed` : '\nall passed');
process.exit(fail ? 1 : 0);
