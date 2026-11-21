// Builds the personal report .docx from DIR/metrics.json, DIR/scores.json, DIR/narrative.json and the charts.
// Usage: node build_report.js --out DIR      (needs the `docx` npm package: npm install --prefix DIR docx@9.5.1)
// Output: DIR/claude-usage-report_<person-slug>_<start>_to_<end>.docx  (no spaces in the file name)
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

const pct = (x, d = 0) => `${(x * 100).toFixed(d)}%`;
const n = (x) => Number(x).toLocaleString('en-US');
const fmtDate = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
const slug = (t) => (t || 'me').toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'me';
const FONT = 'Arial';
const period = `${fmtDate(m.period[0])} – ${fmtDate(m.period[1])}`;

const runs = (parts) => [].concat(parts).map((t) => (typeof t === 'string' ? new TextRun(t) : t));
const p = (text, opts = {}) => new Paragraph({ spacing: { after: 120 }, ...opts, children: runs(text) });
const b = (t) => new TextRun({ text: t, bold: true });
const i = (t) => new TextRun({ text: t, italics: true, color: '52606D' });
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
const den = m.tool_denials || {};
const tok = m.tokens;
const money = (v) => (v == null ? 'N/A' : `${s.currency === 'USD' ? '$' : `${s.currency} `}${Number(v).toFixed(2)}`);
const leverageText = `${s.leverage} / 100 → ${s.tier}${s.champion_capped ? ' (Champion range, capped because prompt quality is below 60)' : ''}${s.leverage_partial ? ' (partial)' : ''}`;
const DIM_LABELS = { goal: 'Goal clarity', context: 'Context', specificity: 'Specificity & constraints', output: 'Output specification', steering: 'Steering & iteration', technique: 'Technique & leverage' };
const readings = nar.dimension_readings || {};

const children = [
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun(`Claude Usage & Prompt Quality Report - ${period}`)] }),
  p([i(`${nar.person || 'Personal report'} · Claude Code${s.plan ? ` · ${s.plan} plan` : ''} · time zone ${m.timezone} · generated ${fmtDate(new Date().toISOString().slice(0, 10))}`)]),

  h1('1. Summary'),
  table(['Measure', 'Result'], [
    ['Personal Leverage Score', leverageText],
    ['Prompt quality', s.quality == null ? 'N/A' : `${s.quality} / 100 (n = ${s.n_judged} sessions judged)`],
    [`Plan fit${s.plan ? ` (${s.plan})` : ''}`, `${s.plan_verdict}${s.plan_verdict_proxy ? ' (proxy)' : ''}: limit hit on ${s.limit_days} of ${m.active_days} active days (${pct(s.limit_day_share)})`],
    ['Activity', `${m.active_working_days}/${m.working_days} working days (${pct(m.active_day_rate)}) + ${m.weekend_active_days} weekend days · ${n(m.prompts)} prompts · ${m.sessions} sessions`],
    ['Cost per active day', s.cost_per_active_day == null ? 'N/A (no plan price given)' : `${money(s.cost_per_active_day)} (at ${money(s.price_month)}/month)`],
  ], [2600, 6426]),
  gap(),
  h2('Biggest wins'),
  ...numbered(titled(nar.wins)),
  h2('Biggest opportunities'),
  ...numbered(titled(nar.opportunities)),

  pageBreak(),
  h1('2. Usage and plan fit'),
  table(['Metric', 'Value'], [
    ['Period / working days', `${period} · ${m.calendar_days} days · ${m.working_days} working days`],
    ['Active days', `${m.active_days} (${m.active_working_days} working, ${m.weekend_active_days} weekend) · longest streak ${m.longest_streak}`],
    ['Prompts', `${n(m.prompts)} · ${m.prompts_per_working_day} per working day · ${m.prompts_per_active_day} per active day`],
    ['Sessions', `${m.sessions} · mean ${m.avg_prompts_per_session} prompts, median ${m.median_prompts_per_session}, max ${m.max_prompts_per_session} · ${pct(m.one_prompt_sessions_pct)} single-prompt`],
    ['How prompts were sent', Object.entries(m.prompt_source).map(([k, v]) => `${k.replace('_', ' ')} ${v}`).join(' · ')],
    ['Prompts by weekday', Object.entries(m.weekday_profile).map(([k, v]) => `${k} ${v}`).join(' · ')],
    ['Top projects (prompts)', m.projects.slice(0, 6).map(([k, v]) => `${k} ${v}`).join(' · ')],
    ['Tool calls (incl. subagents)', `${n(m.tool_calls_total)} · ${m.tool_calls_top.slice(0, 4).map(([k, v]) => `${k} ${n(v)}`).join(', ')}`],
    ['Outcomes', `${n(m.files_edited)} files edited · ${m.git_commit_commands} git commit commands · ${m.prs_linked} PR links · +${n(m.lines_added)} / −${n(m.lines_removed)} lines`],
    ['Tokens', `output ${n(tok.output_tokens || 0)} · cache read ${n(tok.cache_read_input_tokens || 0)} · cache write ${n(tok.cache_creation_input_tokens || 0)} · uncached input ${n(tok.input_tokens || 0)}`],
  ], [2600, 6426]),
  gap(),
  img('chart_weekly.png', 600, 240),
  p([i('Weekly prompts. The first and last bars may cover partial weeks.')], { alignment: AlignmentType.CENTER }),
  img('chart_hours.png', 600, 203),
  p([i(`Prompts by hour (${m.timezone}).`)], { alignment: AlignmentType.CENTER }),
  h2(`Plan fit: ${s.plan_verdict}`),
  p(nar.plan_fit_text || ''),
  ...(nar.plan_fit_actions || []).map((x) => bullet([b(`${x.title}: `), x.text])),

  h1('3. Capabilities'),
  table(['Capability', 'Seen', 'Evidence'], [
    ['MCP tools', m.capabilities['MCP tools'] ? 'Yes' : 'No', m.mcp_servers.slice(0, 5).map(([k, v]) => `${k.replace('plugin_ecc_', '')} ${n(v)}`).join(', ') || '—'],
    ['Skills / slash commands', m.capabilities['Skills / slash commands'] ? 'Yes' : 'No', m.skills_used.slice(0, 5).map(([k, v]) => `${k} ${v}×`).join(', ') || '—'],
    ['Subagents', m.capabilities.Subagents ? 'Yes' : 'No', `${m.subagent_calls} Agent calls`],
    ['Hooks', m.capabilities.Hooks ? 'Yes' : 'No', `${m.hook_sessions} sessions ran Stop hooks`],
    ['Image input', m.capabilities['Image input'] ? 'Yes' : 'No', `${m.images} prompts with images`],
    ['File references', m.capabilities['File references in prompts'] ? 'Yes' : 'No', `${pct(sig.pct_sessions_with_file_or_image)} of sessions reference a file, image or paste`],
    ['Plan mode', m.plan_mode_sessions > 1 ? 'Yes' : m.plan_mode_sessions === 1 ? 'Barely' : 'No', `${m.plan_mode_sessions} sessions`],
    ['Web fetch / search', m.web_calls > 2 ? 'Yes' : m.web_calls > 0 ? 'Barely' : 'No', `${m.web_calls} calls`],
  ], [2400, 900, 5726]),
  gap(),
  p([b('Worth trying, given your mix of use cases:')]),
  ...(nar.capability_suggestions || []).map((x) => bullet([b(`${x.title}. `), x.text])),

  pageBreak(),
  h1('4. Prompt quality'),
  p(`I judged ${s.n_judged} sessions. Each was scored 1–5 on six dimensions against what the task needed. A short prompt that fully serves a simple task can score well.`),
  table(['Dimension', 'Mean (1–5)', 'Reading'], Object.keys(DIM_LABELS).map((k) => [DIM_LABELS[k], dm[k] ?? 'N/A', readings[k] || '']), [2600, 1300, 5126]),
  gap(),
  table(['Signal (all prompts)', 'Value'], [
    ['Median prompt length', `${sig.median_words} words · ${pct(sig.pct_30plus_words)} have 30+ words`],
    ['Names an output format', pct(sig.pct_format_spec)],
    ['Gives context or purpose', pct(sig.pct_context)],
    ['Sessions with a file, image or paste', pct(sig.pct_sessions_with_file_or_image)],
    ['Correction rate (follow-ups)', `${pct(sig.correction_rate, 1)} (pattern-based, probably an undercount)`],
    ['Accepted prompt suggestions', pct(sig.pct_suggestion_accepted)],
  ], [4500, 4526]),
  gap(),
  table(['Mix', 'Sessions'], [
    ...Object.entries(s.use_case_mix).map(([k, v]) => [k, v]),
    ...Object.entries(s.complexity_mix).map(([k, v]) => [`Complexity: ${k}`, `${v} (quality ${s.quality_by_complexity[k] ?? 'N/A'})`]),
  ], [4500, 4526]),
  gap(),
  p([b('Trend. '), `Quality ${s.quality_first ?? 'N/A'} in the first half vs ${s.quality_second ?? 'N/A'} in the second (n = ${s.n_first} vs ${s.n_second}); Leverage Score ${s.leverage_first} → ${s.leverage_second}. `, nar.trend_note || '']),

  h1('5. Coaching'),
  ...(nar.weakest || []).flatMap((x, k) => [h2(`Weakest dimension ${k + 1}: ${x.title}`), p(x.text)]),
  h2('Rewrites of your own prompts'),
  ...(nar.rewrites || []).flatMap((x, k) => [
    p([b(`${k + 1}. ${x.label}`)], { spacing: { before: 120, after: 60 } }),
    p([i('Before: '), new TextRun({ text: x.before, italics: true })], { spacing: { after: 40 } }),
    p([b('After: '), new TextRun(x.after)]),
  ]),
  h2('Five-habit checklist'),
  ...numbered((nar.habits || []).map((x) => [b(`${x.title}: `), x.text])),

  h1('6. Data handling and friction'),
  p([b('Sensitive data: '), `${Object.values(m.data_handling).reduce((a, c) => a + c, 0)} prompts matched the patterns for API keys or tokens, passwords, private keys, card numbers or bulk email lists. `, nar.data_handling_note || '']),
  p([b('Tool-call friction: '), `Tool calls blocked: ${Object.entries(den).map(([k, v]) => `${k} ${n(v)}`).join(', ') || 'none'}. `, nar.friction_note || '']),

  h1('7. Methodology and gaps'),
  bullet([b('Source: '), `Claude Code transcripts in ~/.claude/projects (${m.transcript_files} files on disk, ${m.sessions} sessions with prompts in the period; earliest event ${m.earliest_transcript_event}${m.period_truncated ? '. The period starts before the oldest kept transcript, so the data is truncated' : ''}).`]),
  bullet([b('What counts as a prompt: '), 'a non-subagent user turn with your own text. Excluded: tool results, meta and system messages, task notifications, compaction summaries, ! shell commands and their output. Slash commands and accepted suggestions are counted.']),
  bullet([b('Working days: '), 'Mon–Fri with no holiday adjustment. The active-day rate uses working days only.']),
  bullet([b('Leverage Score: '), `${Object.entries(lp).map(([k, v]) => `${k} ${v}`).join(' + ')} = ${s.leverage}. Engagement = 30×min(1, rate÷0.6); Depth = 15×min(1, prompts per working day÷20); Breadth = 15×min(1, breadth÷6); Quality = 30×quality÷100; Outcomes = 10×mean(1−correction rate, 1−edit-rejection rate). Champion requires quality ≥ 60.`]),
  bullet([b('Prompt quality: '), 'Claude judged the sessions against the rubric in the skill (single rater, so treat it as directional). Signals and the correction rate are regex-based.']),
  bullet([b('Proxies: '), '"PR links" counts distinct PR URLs that appeared in sessions (viewed or created). Tool calls and tokens include subagents. Tokens are shown without a cost.']),
  ...(nar.methodology_extra || []).map((t) => bullet(t)),
];

const doc = new Document({
  creator: 'claude-usage-report skill',
  title: `Claude Usage & Prompt Quality Report - ${period}`,
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal', run: { font: FONT, size: 36, bold: true, color: '1F2933' }, paragraph: { spacing: { before: 0, after: 120 }, keepNext: true } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 28, bold: true, color: '1F3A8A' }, paragraph: { spacing: { before: 320, after: 120 }, keepNext: true, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: 'C7D2E5', space: 2 } } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 23, bold: true, color: '1F2933' }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 1 } },
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
