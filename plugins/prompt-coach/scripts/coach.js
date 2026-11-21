#!/usr/bin/env node
// prompt-coach: UserPromptSubmit hook.
// Reads the hook JSON on stdin. Prints nothing (prompt goes through unchanged), additionalContext (Claude restates
// the prompt and adds a tip), or a block decision (bare paste, while block mode is on).
// Rules: no AI call, no network, never logs prompt text, and FAILS OPEN — any error exits 0 with no output.
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

const DIR = process.env.PROMPT_COACH_DIR || path.join(os.homedir(), '.claude', 'prompt-coach');
const TODAY = new Date().toISOString().slice(0, 10);

const IDE_RE = /<(ide_[a-z_]+)\b[^>]*>[\s\S]*?<\/\1>|<ide_[a-z_]+\b[^>]*\/>/gi;
const PASTE_RE = /<pasted_content[^>]*>[\s\S]*?<\/pasted_content[^>]*>/gi;
const PLACEHOLDER_RE = /\[(Image|Pasted text)[^\]]*\]/gi;
const IMAGE_RE = /\[Image[^\]]*\]|\.(png|jpe?g|gif|webp)\b/i;
const LOG_RE = /(error|exception|traceback|warning|failed|fatal|sqlstate|stack trace|npm err|at [\w.$<>]+ \(|\.php:\d+|\.tsx?:\d+|\.js:\d+|line \d+|exit code|undefined|null)/gi;
const LOG_LINE_RE = new RegExp(LOG_RE.source, 'i');
const DONE_RE = /(done when|should (now )?(show|display|pass|work|be|look|open|return)|expected|verify|confirm|make sure|ensure|run (the )?(tests?|lint|build|pest|phpunit|phpstan|playwright)|tests? (must |should )?pass|until (it|the|all)|acceptance|must (pass|show|work)|check (that|in the browser|on mobile)|at \d{3,4}px|hona chahiye|dikhna chahiye|chalna chahiye|pass hon?a? chahiye|thay tyare|hovu joie)/i;
const VAGUE_RE = /^(pls |please )?(check (this|it|all)|fix (this|it)|still (not|same)|not work(ing)?( proper(ly)?)?|do (continue|it)|continue|proper(ly)?|perfect|same (issue|error|problem)|nai yaar|nahi yaar|maja nai?h?i? aya|kuch (kro|karo)|thik (kro|karo)|sahi (kro|karo)|aur (acha|accha))\b/i;
const SHORT_REPLY_RE = /^(y|yes|yeah|yep|no|nope|ok|okay|k|go|go ahead|continue|proceed|done|thanks|thank you|ty|haan|ha|han|nahi|na|theek hai|thik hai|sahi hai|ho|hā|chalo|option \w|[a-d]|\d+|(\d+\s*[.):-]\s*[\w-]+[\s,]*)+)[.!]*$/i;

const DEFAULT_SETTINGS = { enabled: true, block_mode: 'block', block_until: null, min_words: 12, long_session_prompts: 30, tip_every: 3 };

const MSG = {
  hi: {
    langName: 'Hindi (Devanagari script; keep technical words such as test, plan mode, file names in English)',
    tipPrefix: '💡 टिप:',
    block: (example) => [
      '✋ Prompt coach: आपने सिर्फ़ paste भेजा है, कोई निर्देश नहीं।',
      'Paste के ऊपर एक लाइन जोड़ें: क्या करना है, और काम कब पूरा माना जाए।',
      `उदाहरण: ${example}`,
      '(आपका paste नीचे "Original prompt" में है। उसे copy करें, ऊपर एक लाइन जोड़ें और फिर से भेजें।)',
    ].join('\n'),
    defaultTips: ['अंत में लिखें: "Done when ..." (कौन सा test pass हो या screen पर क्या दिखे)।',
      'एक लाइन में बताएँ क्यों: किसके लिए और क्या समस्या है।',
      'Paste या screenshot के साथ हमेशा एक लाइन लिखें: क्या करना है।',
      '3 से ज़्यादा files वाले काम के लिए पहले plan माँगें (Shift+Tab = plan mode)।'],
    longSession: 'यह session लंबा हो गया है। अगला काम नए session में शुरू करें (या /compact चलाएँ) — इससे जवाब बेहतर और usage कम होगा।',
  },
  gu: {
    langName: 'Gujarati (Gujarati script; keep technical words such as test, plan mode, file names in English)',
    tipPrefix: '💡 ટિપ:',
    block: (example) => [
      '✋ Prompt coach: તમે માત્ર paste મોકલ્યું છે, કોઈ સૂચના નથી.',
      'Paste ની ઉપર એક લાઇન ઉમેરો: શું કરવાનું છે, અને કામ ક્યારે પૂરું ગણાશે.',
      `ઉદાહરણ: ${example}`,
      '(તમારું paste નીચે "Original prompt" માં છે. તેને copy કરો, ઉપર એક લાઇન ઉમેરો અને ફરી મોકલો.)',
    ].join('\n'),
    defaultTips: ['અંતમાં લખો: "Done when ..." (કયો test pass થાય અથવા screen પર શું દેખાય).',
      'એક લાઇનમાં કહો કેમ: કોના માટે અને શું સમસ્યા છે.',
      'Paste કે screenshot સાથે હંમેશા એક લાઇન લખો: શું કરવાનું છે.',
      '3 થી વધુ files વાળા કામ માટે પહેલાં plan માંગો (Shift+Tab = plan mode).'],
    longSession: 'આ session લાંબું થઈ ગયું છે. આગળનું કામ નવા session માં શરૂ કરો (અથવા /compact ચલાવો) — જવાબ વધુ સારા અને usage ઓછું થશે.',
  },
};
const EXAMPLE = 'Fix this error on the checkout page. Done when the payment test passes.';

function readJSON(p, fallback) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return fallback; }
}
function writeJSON(p, v) {
  try { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, JSON.stringify(v)); } catch (e) { /* ignore */ }
}
function log(entry) {
  try { fs.mkdirSync(DIR, { recursive: true }); fs.appendFileSync(path.join(DIR, 'log.jsonl'), JSON.stringify(entry) + '\n'); } catch (e) { /* ignore */ }
}

// Did Claude's last reply end with a question? Then a short prompt is an answer, not a new request.
function lastReplyAsked(transcriptPath) {
  try {
    if (!transcriptPath || !fs.existsSync(transcriptPath)) return false;
    const size = fs.statSync(transcriptPath).size;
    const len = Math.min(size, 96 * 1024);
    const fd = fs.openSync(transcriptPath, 'r');
    const buf = Buffer.alloc(len);
    fs.readSync(fd, buf, 0, len, size - len);
    fs.closeSync(fd);
    const lines = buf.toString('utf8').split('\n').reverse();
    for (const line of lines) {
      if (!line.includes('"type":"assistant"')) continue;
      let e; try { e = JSON.parse(line); } catch (err) { continue; }
      const content = (e.message && e.message.content) || [];
      if (content.some((b) => b && b.type === 'tool_use' && b.name === 'AskUserQuestion')) return true;
      const text = content.filter((b) => b && b.type === 'text').map((b) => b.text).join('\n').trim();
      if (text) return /\?\s*(\*\*)?\s*$/.test(text) || /\?\s*\n/.test(text.slice(-400));
    }
  } catch (e) { /* ignore */ }
  return false;
}

function pickTemplate(profile, text) {
  const t = (profile.templates || []);
  if (!t.length) return null;
  const lc = text.toLowerCase();
  const want = /(ui|button|css|screen|page|modal|responsive|design|layout|footer|header|color|colour)/.test(lc) ? /ui|style|design|screen/i
    : /(test|spec|coverage|playwright|pest)/.test(lc) ? /test/i
      : /(error|bug|fix|issue|crash|fail|not work)/.test(lc) ? /bug|fix|debug|error/i
        : /(feature|add|new|create|build)/.test(lc) ? /feature|build|new/i : null;
  if (!want) return null;
  return t.find((x) => want.test(x.task || '')) || null;
}

function decide(input, profile, state, now) {
  const settings = { ...DEFAULT_SETTINGS, ...(profile.settings || {}) };
  if (settings.enabled === false) return { action: 'off' };
  const lang = MSG[profile.language] ? profile.language : 'hi';
  const M = MSG[lang];
  const raw = String(input.prompt || '');
  const text = raw.replace(IDE_RE, '').trim();
  if (!text) return { action: 'none' };
  if (/^[/!#]/.test(text)) return { action: 'skip-command' };

  const hasPasteTag = /<pasted_content/i.test(text);
  const lines = text.split('\n').length;
  const logHits = (text.match(LOG_RE) || []).length;
  const looksLog = hasPasteTag || (lines >= 4 && logHits >= 2);
  let own = text.replace(PASTE_RE, ' ').replace(PLACEHOLDER_RE, ' ').trim();
  if (looksLog && !hasPasteTag) {
    // An untagged paste: only lines that don't look like log output count as the person's own words.
    own = own.split('\n').filter((l) => !LOG_LINE_RE.test(l) && !/^\s+(at |#\d|\d+\s*\|)/.test(l)).join(' ').trim();
  }
  const ownWords = own.split(/\s+/).filter(Boolean).length;
  const hasImage = IMAGE_RE.test(text);
  const hasDone = DONE_RE.test(own);
  const followup = state.count > 0;
  const flags = [];

  // Short answer to a question Claude just asked: never coach.
  if (followup && ownWords <= 15 && !looksLog && (SHORT_REPLY_RE.test(own) || input._askedLast)) {
    return { action: 'none', flags: ['answer'], ownWords };
  }

  const ctx = [];
  let action = 'none';
  // Layer 2: bare paste / image only.
  const barePaste = looksLog && ownWords < 6;
  const imageOnly = hasImage && ownWords < 4 && !looksLog;
  if (barePaste || imageOnly) {
    flags.push(barePaste ? 'bare_paste' : 'image_only');
    const blockOn = settings.block_mode === 'block' && barePaste && (!settings.block_until || now <= settings.block_until);
    if (blockOn) {
      return { action: 'block', flags, ownWords, output: { decision: 'block', reason: M.block(EXAMPLE) } };
    }
    if (settings.block_mode !== 'off') {
      action = 'ask';
      ctx.push(
        '[prompt-coach] The user sent ' + (barePaste ? 'pasted output (a log or error)' : 'a screenshot') + ' with no instruction.',
        'Do NOT run tools or edit files yet. In one or two lines, say what the paste shows.',
        'Then ask ONE question about what they want (use AskUserQuestion with 2-4 options, such as "Find and fix the cause", "Explain only", "Something else"), and wait.',
        `End with one tip in ${M.langName}, starting with "${M.tipPrefix}": tell them to add one line above a paste — what to do and when it counts as done — with this English example: "${EXAMPLE}"`,
      );
    }
  } else {
    // Layer 1: restate vague or incomplete requests.
    const vague = VAGUE_RE.test(own);
    const shortNoDone = ownWords < settings.min_words && !hasDone;
    const openerNoDone = !followup && !hasDone && ownWords < 40;
    if (vague) flags.push('vague');
    if (shortNoDone) flags.push('short');
    if (!hasDone) flags.push('no_done_check');
    if (vague || shortNoDone || openerNoDone) {
      action = 'coach';
      state.flagged = (state.flagged || 0) + 1;
      const showTip = state.flagged % Math.max(1, settings.tip_every) === 1 || settings.tip_every <= 1;
      const missing = [!hasDone && 'a done-check (how to know it worked)', ownWords < settings.min_words && 'detail about what and where', vague && 'what exactly is wrong or wanted'].filter(Boolean).join(', ');
      ctx.push(
        `[prompt-coach] This message may be missing: ${missing}.`,
        followup
          ? 'Before acting, write ONE line starting with "**Understood:**" that says in simple English what the user most likely means, using the conversation so far.'
          : 'Before acting, write ONE line starting with "**Restated:**" in simple English: "Goal: … | Scope: … | Done when: …". Fill gaps from the conversation and the code; mark guesses with "(?)".',
        'If the goal or the done-check really cannot be inferred and the work would change several files or take more than a few minutes, ask ONE question (AskUserQuestion with 2-4 options) and wait. Otherwise continue with the work using your restated version.',
        'Do not lecture and do not mention this note.',
      );
      if (showTip) {
        const tips = (profile.tips && profile.tips.length ? profile.tips : M.defaultTips);
        const tip = tips[(state.tipsShown || 0) % tips.length];
        state.tipsShown = (state.tipsShown || 0) + 1;
        const tpl = pickTemplate(profile, own);
        ctx.push(`At the very end of your reply, add one short line in ${M.langName}, starting with "${M.tipPrefix}", based on this tip: ${tip}` +
          (tpl ? ` Then show this template on its own line, in English, as "Template: ${tpl.template}"` : ''));
      }
    }
  }

  // Long sessions: one nudge at the threshold, then every 15 prompts.
  const n = state.count + 1;
  const T = settings.long_session_prompts;
  if (T && n >= T && (n === T || (n - T) % 15 === 0)) {
    flags.push('long_session');
    if (action === 'none') action = 'long_session';
    ctx.push(`[prompt-coach] This session now has ${n} prompts. At the end of your reply add one line in ${M.langName}: "${M.tipPrefix} ${M.longSession}"`);
  }

  if (!ctx.length) return { action, flags, ownWords };
  return { action, flags, ownWords, output: { hookSpecificOutput: { hookEventName: 'UserPromptSubmit', additionalContext: ctx.join('\n') } } };
}

function main(stdin) {
  let input;
  try { input = JSON.parse(stdin || '{}'); } catch (e) { return; }
  const profile = readJSON(path.join(DIR, 'profile.json'), {});
  const sid = String(input.session_id || 'nosession').replace(/[^\w-]/g, '').slice(0, 80) || 'nosession';
  const statePath = path.join(DIR, 'state', `${sid}.json`);
  const state = readJSON(statePath, { count: 0, flagged: 0, tipsShown: 0 });
  input._askedLast = state.count > 0 && lastReplyAsked(input.transcript_path);
  const res = decide(input, profile, state, TODAY);
  if (res.action !== 'skip-command') state.count += 1;
  writeJSON(statePath, state);
  log({ ts: new Date().toISOString(), session: sid, words: res.ownWords ?? null, flags: res.flags || [], action: res.action });
  if (res.output) process.stdout.write(JSON.stringify(res.output));
}

module.exports = { decide };

if (require.main === module) {
  let data = '';
  const timer = setTimeout(() => process.exit(0), 4000); // never hold the prompt
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (c) => { data += c; });
  process.stdin.on('end', () => {
    try { main(data); } catch (e) { /* fail open */ }
    clearTimeout(timer);
    process.exit(0);
  });
  process.stdin.on('error', () => process.exit(0));
}
