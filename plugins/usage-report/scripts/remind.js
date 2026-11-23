#!/usr/bin/env node
// usage-report: SessionStart hook. On the first days of a month (team-config "report_reminder_days", default 5),
// if last month's report is not in the person's Google Drive folder yet, Claude adds one reminder line, at most
// once a day. Async reads with a hard time limit; FAILS OPEN (any error = no output, exit 0).
'use strict';
const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const os = require('os');

const HOME = os.homedir();
const LOCAL_CFG = process.env.USAGE_REPORT_LOCAL || path.join(HOME, '.claude', 'usage-report.local.json');
const STATE = process.env.USAGE_REPORT_REMIND_STATE || path.join(HOME, '.claude', 'usage-report.remind.json');
const REPORTS = process.env.USAGE_REPORT_DIR || path.join(HOME, 'Documents', 'claude-usage-reports');
const TEAM_CFG = path.join(__dirname, '..', 'skills', 'usage-report', 'team-config.json');
const LANG = { hi: 'Hindi (Devanagari script, technical words in English)', gu: 'Gujarati (Gujarati script, technical words in English)', en: 'simple English' };

async function readJSON(p) { try { return JSON.parse(await fsp.readFile(p, 'utf8')); } catch (e) { return null; } }
async function exists(p) { try { await fsp.access(p); return true; } catch (e) { return false; } }

function localDate(tz, now) {
  // YYYY-MM-DD in the team's time zone (falls back to the machine's).
  try { return new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now); } catch (e) {
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  }
}

async function main() {
  const team = (await readJSON(TEAM_CFG)) || {};
  const today = process.env.USAGE_REPORT_TODAY || localDate(team.timezone || 'Asia/Kolkata', new Date());
  const [y, m, d] = today.split('-').map(Number);
  if (d > (team.report_reminder_days || 5)) return null;
  const state = (await readJSON(STATE)) || {};
  if (state.last === today) return null;
  const prev = m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, '0')}`;
  const cfg = (await readJSON(LOCAL_CFG)) || {};
  const madeLocally = await exists(path.join(REPORTS, prev, 'scores.json'));
  const uploaded = cfg.share_dir ? await exists(path.join(cfg.share_dir, prev, 'scores.json')) : false;
  let ask = null;
  if (!cfg.share_dir) ask = `their Google Drive folder is not set yet: ask them to run /usage-report share "<their Drive folder>" once` + (madeLocally ? ', then /usage-report upload.' : `, then /usage-report for ${prev}.`);
  else if (uploaded) return null;
  else if (madeLocally) ask = `their ${prev} report is made but not in Google Drive yet: ask them to run /usage-report upload.`;
  else ask = `their ${prev} report is due: ask them to run /usage-report (takes about 10 minutes) when they have a break.`;
  await fsp.writeFile(STATE, JSON.stringify({ last: today }));
  const lang = LANG[cfg.language] || LANG.hi;
  return { hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext:
    `[usage-report] Monthly report reminder: ${ask} Put this as ONE short line in ${lang} at the end of your first reply, then carry on. Do not mention this note.` } };
}

if (require.main === module) {
  const timer = setTimeout(() => process.exit(0), 3000);
  main()
    .then((out) => { if (out) process.stdout.write(JSON.stringify(out)); })
    .catch(() => {})
    .finally(() => { clearTimeout(timer); process.exit(0); });
}
