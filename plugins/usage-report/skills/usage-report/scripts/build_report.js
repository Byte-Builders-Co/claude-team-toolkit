// Builds the personal report .docx from DIR/metrics.json, DIR/scores.json, DIR/narrative.json and the charts.
// Usage: node build_report.js --out DIR      (needs the `docx` npm package: npm install --prefix DIR docx@9.5.1)
// Output: DIR/claude-usage-report_<person-slug>_<start>_to_<end>.docx  (no spaces in the file name)
// Language: team-config.json "report_language" ("en" for Byte-Builders: the lead reads everyone's report) wins;
// otherwise narrative.language = "en" (default), "hi" or "gu". Headings and labels follow it.
const fs = require('fs');
const path = require('path');

const argOut = process.argv.indexOf('--out');
if (argOut < 0) { console.error('usage: node build_report.js --out DIR'); process.exit(1); }
const DIR = path.resolve(process.argv[argOut + 1].replace(/^~/, require('os').homedir()));
const docx = require(require.resolve('docx', { paths: [DIR, __dirname] }));
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  HeadingLevel, AlignmentType, ImageRun, LevelFormat, BorderStyle, PageBreak,
} = docx;

const read = (f) => JSON.parse(fs.readFileSync(path.join(DIR, f), 'utf8'));
const m = read('metrics.json');
const s = read('scores.json');
const nar = read('narrative.json');
let CFG = {};
try { CFG = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'team-config.json'), 'utf8')); } catch (e) { /* defaults */ }
const pickLang = (v) => (['hi', 'gu', 'en'].includes(v) ? v : null);
const LANG = pickLang(CFG.report_language) || pickLang(nar.language) || 'en';
if (LANG === 'en') {
  // coach_tips go to the person's prompt coach (their own language) and are not printed in the report.
  const { coach_tips, ...printed } = nar;
  const bad = [];
  const walk = (v, at) => {
    if (typeof v === 'string') { if (/[ऀ-ॿ઀-૿]/.test(v)) bad.push(at); }
    else if (Array.isArray(v)) v.forEach((x, i) => walk(x, `${at}[${i}]`));
    else if (v && typeof v === 'object') Object.entries(v).forEach(([k, x]) => walk(x, at ? `${at}.${k}` : k));
  };
  walk(printed, '');
  if (bad.length) console.error(`WARNING: report language is English but these narrative.json fields have Hindi/Gujarati text: ${bad.slice(0, 15).join(', ')}${bad.length > 15 ? ' …' : ''}. Rewrite them in simple English and build again.`);
}

// ---- labels -------------------------------------------------------------------------------
const T = {
  title: { en: 'Claude Usage & Prompt Quality Report', hi: 'Claude उपयोग और Prompt गुणवत्ता रिपोर्ट', gu: 'Claude ઉપયોગ અને Prompt ગુણવત્તા રિપોર્ટ' },
  summary: { en: 'Summary', hi: 'सारांश', gu: 'સારાંશ' },
  measure: { en: 'Measure', hi: 'माप', gu: 'માપ' },
  result: { en: 'Result', hi: 'परिणाम', gu: 'પરિણામ' },
  leverage: { en: 'Leverage Score', hi: 'Leverage Score', gu: 'Leverage Score' },
  quality: { en: 'Prompt quality', hi: 'Prompt गुणवत्ता', gu: 'Prompt ગુણવત્તા' },
  planfit: { en: 'Plan fit', hi: 'Plan fit', gu: 'Plan fit' },
  activity: { en: 'Activity', hi: 'गतिविधि', gu: 'પ્રવૃત્તિ' },
  cost: { en: 'Cost per active day', hi: 'प्रति सक्रिय दिन लागत', gu: 'સક્રિય દિવસ દીઠ ખર્ચ' },
  wins: { en: 'Biggest wins', hi: 'सबसे बड़ी अच्छी बातें', gu: 'સૌથી મોટી સારી બાબતો' },
  opps: { en: 'Biggest opportunities', hi: 'सुधार के सबसे बड़े मौके', gu: 'સુધારાની સૌથી મોટી તકો' },
  progress: { en: 'Progress since last month', hi: 'पिछले महीने से प्रगति', gu: 'ગયા મહિનાથી પ્રગતિ' },
  kpi: { en: 'KPI', hi: 'KPI', gu: 'KPI' },
  prev: { en: 'Last month', hi: 'पिछला महीना', gu: 'ગયો મહિનો' },
  now: { en: 'This month', hi: 'यह महीना', gu: 'આ મહિનો' },
  change: { en: 'Change', hi: 'बदलाव', gu: 'ફેરફાર' },
  better: { en: 'better', hi: 'बेहतर', gu: 'સારું' },
  worse: { en: 'worse', hi: 'कमज़ोर', gu: 'નબળું' },
  same: { en: 'same', hi: 'वही', gu: 'એ જ' },
  notmeasured: { en: 'not measured', hi: 'मापा नहीं गया', gu: 'માપ્યું નથી' },
  targetsLast: { en: "Last month's targets", hi: 'पिछले महीने के लक्ष्य', gu: 'ગયા મહિનાના લક્ષ્યો' },
  target: { en: 'Target', hi: 'लक्ष्य', gu: 'લક્ષ્ય' },
  met: { en: 'Met', hi: 'पूरा हुआ', gu: 'પૂરું થયું' },
  notmet: { en: 'Not yet', hi: 'अभी नहीं', gu: 'હજુ નહીં' },
  usage: { en: 'Usage and plan fit', hi: 'उपयोग और plan fit', gu: 'ઉપયોગ અને plan fit' },
  metric: { en: 'Metric', hi: 'मीट्रिक', gu: 'મેટ્રિક' },
  value: { en: 'Value', hi: 'मान', gu: 'મૂલ્ય' },
  caps: { en: 'Capabilities and project setup', hi: 'Capabilities और project setup', gu: 'Capabilities અને project setup' },
  capability: { en: 'Capability', hi: 'Capability', gu: 'Capability' },
  seen: { en: 'Used', hi: 'उपयोग', gu: 'ઉપયોગ' },
  evidence: { en: 'Evidence', hi: 'प्रमाण', gu: 'પુરાવો' },
  worth: { en: 'Worth trying, given your work:', hi: 'आपके काम के हिसाब से आज़माने लायक:', gu: 'તમારા કામ મુજબ અજમાવવા જેવું:' },
  project: { en: 'Project', hi: 'Project', gu: 'Project' },
  pq: { en: 'Prompt quality', hi: 'Prompt गुणवत्ता', gu: 'Prompt ગુણવત્તા' },
  dimension: { en: 'Dimension', hi: 'आयाम', gu: 'પરિમાણ' },
  mean: { en: 'Mean (1–5)', hi: 'औसत (1–5)', gu: 'સરેરાશ (1–5)' },
  reading: { en: 'What it means', hi: 'मतलब', gu: 'અર્થ' },
  signal: { en: 'Signal (all prompts)', hi: 'संकेत (सभी prompts)', gu: 'સંકેત (બધા prompts)' },
  mix: { en: 'Mix', hi: 'प्रकार', gu: 'પ્રકાર' },
  sessions: { en: 'Sessions', hi: 'Sessions', gu: 'Sessions' },
  coaching: { en: 'Coaching', hi: 'Coaching', gu: 'Coaching' },
  weakest: { en: 'Weakest area', hi: 'सबसे कमज़ोर हिस्सा', gu: 'સૌથી નબળો ભાગ' },
  rewrites: { en: 'Your own prompts, rewritten', hi: 'आपके अपने prompts, बेहतर रूप में', gu: 'તમારા પોતાના prompts, વધુ સારા રૂપમાં' },
  before: { en: 'Before', hi: 'पहले', gu: 'પહેલાં' },
  after: { en: 'After', hi: 'बाद में', gu: 'પછી' },
  why: { en: 'Why', hi: 'क्यों', gu: 'કેમ' },
  templates: { en: 'Your prompt templates (fill in the blanks)', hi: 'आपके prompt templates (खाली जगह भरें)', gu: 'તમારા prompt templates (ખાલી જગ્યા ભરો)' },
  expensive: { en: 'Your most expensive session', hi: 'आपका सबसे महँगा session', gu: 'તમારું સૌથી મોંઘું session' },
  better_prompt: { en: 'A prompt that would have avoided it', hi: 'यह prompt इसे टाल सकता था', gu: 'આ prompt તેને ટાળી શક્યું હોત' },
  lesson: { en: 'Lesson', hi: 'सीख', gu: 'શીખ' },
  next: { en: 'Next month', hi: 'अगला महीना', gu: 'આવતો મહિનો' },
  targets: { en: 'Your 3 targets', hi: 'आपके 3 लक्ष्य', gu: 'તમારા 3 લક્ષ્યો' },
  habits: { en: 'Five-habit checklist', hi: 'पाँच आदतों की checklist', gu: 'પાંચ ટેવોની checklist' },
  files: { en: 'Ready-made files for you', hi: 'आपके लिए तैयार files', gu: 'તમારા માટે તૈયાર files' },
  data: { en: 'Data handling and friction', hi: 'Data handling और रुकावटें', gu: 'Data handling અને અડચણો' },
  sensitive: { en: 'Sensitive data', hi: 'संवेदनशील data', gu: 'સંવેદનશીલ data' },
  friction: { en: 'Tool-call friction', hi: 'Tool-call रुकावटें', gu: 'Tool-call અડચણો' },
  method: { en: 'Methodology and gaps', hi: 'Methodology और सीमाएँ', gu: 'Methodology અને મર્યાદાઓ' },
};
const L = (k) => (T[k] ? T[k][LANG] || T[k].en : k);
const DIM_LABELS = {
  goal: { en: 'Goal clarity', hi: 'लक्ष्य की स्पष्टता', gu: 'લક્ષ્યની સ્પષ્ટતા' },
  context: { en: 'Context', hi: 'संदर्भ (context)', gu: 'સંદર્ભ (context)' },
  specificity: { en: 'Specificity & constraints', hi: 'स्पष्ट शर्तें', gu: 'સ્પષ્ટ શરતો' },
  output: { en: 'Output specification ("done when")', hi: 'Output / "done when"', gu: 'Output / "done when"' },
  steering: { en: 'Steering & follow-ups', hi: 'Follow-ups', gu: 'Follow-ups' },
  technique: { en: 'Technique & leverage', hi: 'तकनीक (plan mode, tests, files)', gu: 'ટેકનિક (plan mode, tests, files)' },
};
const KPI_LABELS = {
  quality: { hi: 'Prompt गुणवत्ता', gu: 'Prompt ગુણવત્તા' },
  quality_quick: { hi: 'छोटे कामों पर गुणवत्ता', gu: 'નાના કામો પર ગુણવત્તા' },
  output_dim: { hi: 'Output / "done when" (1–5)', gu: 'Output / "done when" (1–5)' },
  pct_done_check: { hi: '"Done when" बताने वाले prompts', gu: '"Done when" કહેતા prompts' },
  pct_bare_paste: { hi: 'बिना निर्देश के paste', gu: 'સૂચના વગરના paste' },
  plan_on_big_rate: { hi: 'बड़े कामों पर plan mode', gu: 'મોટા કામો પર plan mode' },
  verify_rate: { hi: 'Sessions जहाँ tests/lint चले', gu: 'Sessions જ્યાં tests/lint ચાલ્યા' },
  avg_prompts_per_session: { hi: 'प्रति session prompts', gu: 'session દીઠ prompts' },
  pct_prompts_in_long_sessions: { hi: '30+ prompt वाले sessions में prompts', gu: '30+ prompt વાળા sessions માં prompts' },
  correction_rate: { hi: 'दोबारा पूछना / सुधार', gu: 'ફરી પૂછવું / સુધારો' },
  limit_days: { hi: 'Usage-limit वाले दिन', gu: 'Usage-limit વાળા દિવસો' },
  data_flags: { hi: 'संवेदनशील data flags', gu: 'સંવેદનશીલ data flags' },
  active_day_rate: { hi: 'सक्रिय कार्य-दिवस', gu: 'સક્રિય કાર્ય-દિવસો' },
  leverage: { hi: 'Leverage Score', gu: 'Leverage Score' },
};
const PCT_KPIS = new Set(['pct_done_check', 'pct_bare_paste', 'plan_on_big_rate', 'verify_rate', 'pct_prompts_in_long_sessions', 'correction_rate', 'active_day_rate']);

const pct = (x, d = 0) => (x == null ? 'N/A' : `${(x * 100).toFixed(d)}%`);
const n = (x) => Number(x).toLocaleString('en-US');
const fmtDate = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
const slug = (t) => (t || 'me').toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'me';
const FONT = { ascii: 'Arial', hAnsi: 'Arial', eastAsia: 'Arial', cs: 'Nirmala UI' };
const period = `${fmtDate(m.period[0])} – ${fmtDate(m.period[1])}`;
const fmtKpi = (k, v) => (v == null ? L('notmeasured') : PCT_KPIS.has(k) ? pct(v) : String(v));

const runs = (parts) => [].concat(parts).map((t) => (typeof t === 'string' ? new TextRun(t) : t));
const p = (text, opts = {}) => new Paragraph({ spacing: { after: 120 }, ...opts, children: runs(text) });
const b = (t) => new TextRun({ text: t, bold: true });
const i = (t) => new TextRun({ text: t, italics: true, color: '52606D' });
const mono = (t) => new TextRun({ text: t, font: { ascii: 'Consolas', hAnsi: 'Consolas', cs: 'Nirmala UI', eastAsia: 'Consolas' }, size: 19 });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const bullet = (parts) => new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { after: 60 }, children: runs(parts) });
let listId = 0;
const numbered = (items) => { listId += 1; return items.map((parts) => new Paragraph({ numbering: { reference: 'numbers', level: 0, instance: listId }, spacing: { after: 60 }, children: runs(parts) })); };
const titled = (items = []) => items.map((x) => [b(`${x.title}. `), x.text]);
const gap = () => new Paragraph({ spacing: { after: 80 }, children: [] });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });
const img = (file, w, h) => (fs.existsSync(path.join(DIR, file))
  ? new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: 'png', data: fs.readFileSync(path.join(DIR, file)), transformation: { width: w, height: h } })] })
  : p([i(`(chart ${file} not generated)`)]));

function table(header, rows, widths) {
  const total = widths.reduce((a, c) => a + c, 0);
  const cell = (text, isHead, w) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: isHead ? { type: ShadingType.CLEAR, color: 'auto', fill: 'E8EEF9' } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: String(text ?? 'N/A'), bold: isHead, size: 19 })] })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: header.map((t, k) => cell(t, true, widths[k])) }),
      ...rows.map((r) => new TableRow({ children: r.map((t, k) => cell(t, false, widths[k])) })),
    ],
  });
}

const dm = s.dimension_means;
const lp = s.leverage_parts;
const sig = m.signals;
const pr = m.practices || {};
const den = m.tool_denials || {};
const tok = m.tokens;
const money = (v) => (v == null ? 'N/A' : `${s.currency === 'USD' ? '$' : `${s.currency} `}${Number(v).toFixed(2)}`);
const leverageText = `${s.leverage} / 100 → ${s.tier}${s.champion_capped ? ' (Champion range, capped: prompt quality < 60)' : ''}${s.leverage_partial ? ' (partial)' : ''}`;
const readings = nar.dimension_readings || {};
const prog = s.progress;
const workdaysText = (m.workdays || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']).join(', ');

const progressSection = !prog ? [] : [
  h1(L('progress')),
  p([i(`${fmtDate(prog.prev_period[0])} – ${fmtDate(prog.prev_period[1])} → ${period}${prog.prev_method_version < 2 ? ' · last month used the v1 method, so some KPIs were not measured then' : ''}`)]),
  table([L('kpi'), L('prev'), L('now'), L('change')], Object.entries(prog.kpis).map(([k, v]) => [
    (KPI_LABELS[k] && KPI_LABELS[k][LANG]) || v.label, fmtKpi(k, v.prev), fmtKpi(k, v.now),
    v.change == null ? '—' : v.improved == null ? L('same') : v.improved ? `▲ ${L('better')}` : `▼ ${L('worse')}`,
  ]), [3800, 1700, 1700, 1826]),
  gap(),
  ...(prog.targets && prog.targets.length ? [
    h2(L('targetsLast')),
    table([L('kpi'), L('target'), L('now'), ''], prog.targets.map((t) => [
      (KPI_LABELS[t.metric] && KPI_LABELS[t.metric][LANG]) || t.label, fmtKpi(t.metric, t.target), fmtKpi(t.metric, t.now),
      t.met == null ? L('notmeasured') : t.met ? `✔ ${L('met')}` : L('notmet'),
    ]), [3800, 1700, 1700, 1826]),
  ] : []),
  ...(nar.progress_note ? [p(nar.progress_note)] : []),
];

const setupRows = (m.project_setup || []).slice(0, 8).map((x) => [x.project, x.claude_md ? '✔' : '✘', x.hooks ? '✔' : '✘', x.allowlist ? `✔ (${x.allowlist})` : '✘']);
const exp = nar.expensive_session;

const children = [
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun(`${L('title')} - ${period}`)] }),
  p([i(`${nar.person || 'Personal report'} · Claude Code${s.plan ? ` · ${s.plan} plan` : ''} · ${m.timezone} · ${workdaysText} · generated ${fmtDate(new Date().toISOString().slice(0, 10))}`)]),

  h1(`1. ${L('summary')}`),
  table([L('measure'), L('result')], [
    [L('leverage'), leverageText],
    [L('quality'), s.quality == null ? 'N/A' : `${s.quality} / 100 (n = ${s.n_judged})`],
    [`${L('planfit')}${s.plan ? ` (${s.plan})` : ''}`, `${s.plan_verdict}${s.plan_verdict_proxy ? ' (proxy)' : ''}: ${s.limit_days} / ${m.active_days} (${pct(s.limit_day_share)})`],
    [L('activity'), `${m.active_working_days}/${m.working_days} (${pct(m.active_day_rate)}) + ${m.non_working_active_days ?? m.weekend_active_days} · ${n(m.prompts)} prompts · ${m.sessions} sessions`],
    [L('cost'), s.cost_per_active_day == null ? 'N/A' : `${money(s.cost_per_active_day)} (${money(s.price_month)}/month)`],
  ], [2600, 6426]),
  gap(),
  h2(L('wins')),
  ...numbered(titled(nar.wins)),
  h2(L('opps')),
  ...numbered(titled(nar.opportunities)),

  ...progressSection,

  pageBreak(),
  h1(`2. ${L('usage')}`),
  table([L('metric'), L('value')], [
    ['Period / working days', `${period} · ${m.calendar_days} days · ${m.working_days} working days (${workdaysText}${(m.holidays_in_period || []).length ? `; ${m.holidays_in_period.length} holidays excluded` : ''})`],
    ['Active days', `${m.active_days} (${m.active_working_days} working, ${m.non_working_active_days ?? m.weekend_active_days} other) · longest streak ${m.longest_streak}`],
    ['Prompts', `${n(m.prompts)} · ${m.prompts_per_working_day} per working day · housekeeping commands not counted: ${Object.entries(m.housekeeping_commands || {}).map(([k, v]) => `${k} ${v}`).join(', ') || 'none'}`],
    ['Sessions', `${m.sessions} · mean ${m.avg_prompts_per_session}, median ${m.median_prompts_per_session}, max ${m.max_prompts_per_session} · ${pct(m.pct_prompts_in_long_sessions)} of prompts in 30+ prompt sessions`],
    ['Top projects (prompts)', m.projects.slice(0, 6).map(([k, v]) => `${k} ${v}`).join(' · ')],
    ['Outcomes', `${n(m.files_edited)} files edited · +${n(m.lines_added)} / −${n(m.lines_removed)} lines · commits run by Claude ${m.claude_commit_commands ?? m.git_commit_commands} · your own commits ${m.own_commits ?? 'N/A'} · PR links ${m.prs_linked}`],
    ['Habits', `tests/lint run in ${pct(pr.verify_rate)} of sessions with edits · plan mode on ${pct(pr.plan_on_big_rate)} of big sessions · ${m.interrupts ?? 0} interrupts`],
    ['Tokens', `output ${n(tok.output_tokens || 0)} · cache read ${n(tok.cache_read_input_tokens || 0)} · cache write ${n(tok.cache_creation_input_tokens || 0)}`],
  ], [2600, 6426]),
  gap(),
  img('chart_weekly.png', 600, 240),
  img('chart_hours.png', 600, 203),
  h2(`${L('planfit')}: ${s.plan_verdict}`),
  p(nar.plan_fit_text || ''),
  ...(nar.plan_fit_actions || []).map((x) => bullet([b(`${x.title}: `), x.text])),

  h1(`3. ${L('caps')}`),
  table([L('capability'), L('seen'), L('evidence')], [
    ['MCP tools', m.capabilities['MCP tools'] ? '✔' : '✘', m.mcp_servers.slice(0, 5).map(([k, v]) => `${k} ${n(v)}`).join(', ') || '—'],
    ['Skills / slash commands', m.capabilities['Skills / slash commands'] ? '✔' : '✘', m.skills_used.slice(0, 5).map(([k, v]) => `${k} ${v}×`).join(', ') || '—'],
    ['Subagents', m.capabilities.Subagents ? '✔' : '✘', `${m.subagent_calls}`],
    ['Hooks', m.capabilities.Hooks ? '✔' : '✘', `user settings ${m.hooks_configured?.user_settings ? '✔' : '✘'} · projects ${m.hooks_configured?.projects ?? 0} · prompt coach ${m.hooks_configured?.prompt_coach ? '✔' : '✘'}`],
    ['Plan mode', m.plan_mode_sessions ? '✔' : '✘', `${m.plan_mode_sessions} sessions`],
    ['Image input', m.capabilities['Image input'] ? '✔' : '✘', `${m.images}`],
    ['Web fetch / search', m.web_calls ? '✔' : '✘', `${m.web_calls}`],
  ], [2400, 900, 5726]),
  gap(),
  ...(setupRows.length ? [table([L('project'), 'CLAUDE.md', 'Hooks', 'Allowlist'], setupRows, [3600, 1800, 1800, 1826]), gap()] : []),
  p([b(L('worth'))]),
  ...(nar.capability_suggestions || []).map((x) => bullet([b(`${x.title}. `), x.text])),

  pageBreak(),
  h1(`4. ${L('pq')}`),
  table([L('dimension'), L('mean'), L('reading')], Object.keys(DIM_LABELS).map((k) => [DIM_LABELS[k][LANG] || DIM_LABELS[k].en, dm[k] ?? 'N/A', readings[k] || '']), [2600, 1300, 5126]),
  gap(),
  table([L('signal'), L('value')], [
    ['"Done when" / verification named', pct(sig.pct_done_check)],
    ['Pastes or images with no instruction', `${pct(sig.pct_bare_paste)} · ${pct(sig.pct_image_only)}`],
    ['Median prompt length (own words)', `${sig.median_words}`],
    ['Gives context or purpose', pct(sig.pct_context)],
    ['Names an output format', pct(sig.pct_format_spec)],
    ['Correction rate (follow-ups)', pct(sig.correction_rate, 1)],
  ], [4500, 4526]),
  gap(),
  table([L('mix'), L('sessions')], [
    ...Object.entries(s.use_case_mix).map(([k, v]) => [k, `${v} (quality ${s.quality_by_use_case?.[k] ?? 'N/A'})`]),
    ...Object.entries(s.complexity_mix).map(([k, v]) => [`Complexity: ${k}`, `${v} (quality ${s.quality_by_complexity[k] ?? 'N/A'})`]),
  ], [4500, 4526]),
  gap(),
  p([b('Trend. '), nar.trend_note || '']),

  h1(`5. ${L('coaching')}`),
  ...(nar.weakest || []).flatMap((x, k) => [h2(`${L('weakest')} ${k + 1}: ${x.title}`), p(x.text)]),
  h2(L('rewrites')),
  ...(nar.rewrites || []).flatMap((x, k) => [
    p([b(`${k + 1}. ${x.label}`)], { spacing: { before: 120, after: 60 } }),
    p([i(`${L('before')}: `), new TextRun({ text: x.before, italics: true })], { spacing: { after: 40 } }),
    p([b(`${L('after')}: `), new TextRun(x.after)], { spacing: { after: 40 } }),
    ...(x.why ? [p([i(`${L('why')}: `), x.why])] : []),
  ]),
  h2(L('templates')),
  ...(nar.templates || []).flatMap((x) => [
    p([b(x.task)], { spacing: { before: 100, after: 40 } }),
    p([mono(x.template)], { spacing: { after: 40 } }),
    ...(x.tip ? [p([i(x.tip)])] : []),
  ]),
  ...(exp ? [
    h2(`${L('expensive')}: ${exp.title || ''}`),
    p(exp.what_happened || ''),
    ...(exp.cost ? [p([i(exp.cost)])] : []),
    p([b(`${L('better_prompt')}: `)], { spacing: { after: 40 } }),
    p([mono(exp.better_prompt || '')]),
    p([b(`${L('lesson')}: `), exp.lesson || '']),
  ] : []),

  h1(`6. ${L('next')}`),
  h2(L('targets')),
  ...numbered((nar.targets || []).map((t) => [b(`${(KPI_LABELS[t.metric] && KPI_LABELS[t.metric][LANG]) || t.metric}: ${fmtKpi(t.metric, s.kpis?.[t.metric])} → ${fmtKpi(t.metric, t.target)}. `), t.text || ''])),
  h2(L('habits')),
  ...numbered((nar.habits || []).map((x) => [b(`${x.title}: `), x.text])),
  h2(L('files')),
  bullet([mono('suggested/CLAUDE.md-snippet.md'), ' — CLAUDE.md']),
  bullet([mono('suggested/settings.allowlist.json'), ' — .claude/settings.json → permissions.allow']),
  bullet([mono('suggested/commands/*.md'), ' — .claude/commands/']),

  h1(`7. ${L('data')}`),
  p([b(`${L('sensitive')}: `), `${Object.values(m.data_handling).reduce((a, c) => a + c, 0)} flags. `, nar.data_handling_note || '']),
  p([b(`${L('friction')}: `), `${Object.entries(den).map(([k, v]) => `${k} ${n(v)}`).join(', ') || 'none'}. `, nar.friction_note || '']),

  h1(`8. ${L('method')}`),
  bullet([b('Source: '), `Claude Code transcripts in ~/.claude/projects (${m.transcript_files} files; earliest event ${m.earliest_transcript_event}${m.period_truncated ? '; the period starts before the oldest kept transcript, so the data is truncated' : ''}). cleanupPeriodDays: ${m.cleanup_period_days ?? 'not set (30)'}.`]),
  bullet([b('Method v2. '), 'A prompt is your own text in a main-session user turn. Not counted: tool results, system and hook messages, IDE auto-attached context, interrupt markers, and housekeeping slash commands such as /clear, /login and /compact.']),
  bullet([b('Working days: '), `${workdaysText}, minus the team holidays in team-config.json.`]),
  bullet([b('Leverage Score v2: '), `${Object.entries(lp).map(([k, v]) => `${k} ${v}`).join(' + ')} = ${s.leverage}. Engagement 20×min(1, rate÷0.7); Depth 10×min(1, prompts per working day÷20); Breadth 10×min(1, capabilities÷6); Quality 30×quality÷100; Practices 20×mean(done-check÷40%, verify÷60%, plan-on-big÷50%, 1−long-session share÷50%); Outcomes 10×mean(1−correction rate, 1−edit-rejection rate). Champion needs quality ≥ 60.`]),
  bullet([b('Prompt quality: '), 'Claude judged the sampled sessions against the rubric with anchor examples, seeing each session\'s outcome (follow-ups, interrupts, tests run). Spelling, grammar and Hindi/Gujarati/Hinglish are never penalised. Single rater: treat it as directional.']),
  ...(nar.methodology_extra || []).map((t) => bullet(t)),
];

const doc = new Document({
  creator: 'usage-report skill',
  title: `${L('title')} - ${period}`,
  styles: {
    default: { document: { run: { font: FONT, size: 21, sizeComplexScript: 21 } } },
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal', run: { font: FONT, size: 34, sizeComplexScript: 34, bold: true, color: '1F2933' }, paragraph: { spacing: { before: 0, after: 120 }, keepNext: true } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 28, sizeComplexScript: 28, bold: true, color: '1F3A8A' }, paragraph: { spacing: { before: 320, after: 120 }, keepNext: true, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: 'C7D2E5', space: 2 } } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 23, sizeComplexScript: 23, bold: true, color: '1F2933' }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] },
      { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] },
    ],
  },
  sections: [{ properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children }],
});

const out = path.join(DIR, `claude-usage-report_${slug(nar.person)}_${m.period[0]}_to_${m.period[1]}.docx`);
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log(out); });
