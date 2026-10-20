// The server draws its menus for a telnet terminal: boxes of ╔═╗║ (or +=+|), rules of ═══ or
// ----, titles between rules. /play shows them in its own dress instead (theme.css, hud.css .tx-*):
//   a little box round a title or two (TUTORIAL COMPLETE, a discovery, a level gained) is a banner;
//   a bigger box (score, a shop's list, who) is a panel, its rows kept in step (fixed width) but
//     its frame drawn by the panel, its inner rules as hairlines, its column bars faint;
//   a rule alone is the diamond rule, and a title between rules, or on one, a heading.
// Pure (no DOM), so it runs in Node tests. Lines come as {html, text}: html as the bridge made it
// (ansi spans, web_client.py), text the same without tags.

const RULE_CH = '═─━=\\-~*';
const RULE = new RegExp(`^\\s*[╔╚╠╟╞╒╘┌└├+]?[${RULE_CH}+╦╩╤╧┬┴┼╬]{4,}[╗╝╣╢╡╕╛┐┘┤+]?\\s*$`);
// a title on a rule: "═══ QUEST COMPLETE ═══", "---- Spells ----", "== Shop ==" (letters inside)
const TITLED = new RegExp(`^\\s*[╔╚╠+]?[${RULE_CH}]{2,}\\s*([^${RULE_CH}║│|].*?)\\s*[${RULE_CH}]{2,}[╗╝╣+]?\\s*$`);
// a row in a box: a bar at each end (or at the start of a box's row)
const ROW = /^\s*[║│|]\s?(.*?)\s*[║│|]?\s*$/;
const BAR = /[║│|]/;

// what a line is: 'rule', 'titled' (a heading on a rule), 'row' (inside a box) or 'text'
export function classify(text) {
  const t = String(text || '').replace(/\s+$/, '');
  if (!t.trim()) return { t: 'blank' };
  if (RULE.test(t) && /[═─━=\-~]{3}/.test(t)) return { t: 'rule', inner: /^\s*[╠╟╞├]/.test(t) || /^\s*\+-/.test(t) };
  const m = t.match(TITLED);
  if (m && /[A-Za-z]/.test(m[1]) && !BAR.test(m[1])) return { t: 'titled', title: m[1].replace(/^[\s★☆✦✧•*]+|[\s★☆✦✧•*]+$/g, '') };
  // (a lone "|" is a map's path, not a box: a row has room inside its bars)
  if ((/^\s*[║│]/.test(t) || (/^\s*\|/.test(t) && /\|\s*$/.test(t))) && t.trim().length >= 3) return { t: 'row', text: t.match(ROW)[1] };
  if (columns(t)) return { t: 'cols' };
  return { t: 'text' };
}

// a row of a list the server set in columns with spaces ("  horse      2000 gold  A riding horse",
// "absolution    accept    account"): an indented line of two fields or more, or any of three,
// each short; prose, with a double space after a full stop, is not one
function columns(t) {
  const parts = t.trim().split(/\s{2,}/);
  if (parts.length < 2 || parts.slice(0, -1).some(p => p.length > 32)) return false;
  // a status line strung with " | " is a phrase, not a row ("Kills: 0  |  Rooms explored: 627")
  if (parts.some(p => p.startsWith('|'))) return false;
  if (/^\s/.test(t)) return true;          // (indented, its last field may run on, a description)
  // a label and its value set apart ("Level 11:      23,140 XP"), or three short fields or more
  if (parts.length === 2) return /^[\w' -]{1,24}:$/.test(parts[0]) && parts[1].length <= 32;
  return parts.every(p => p.length <= 32);
}

// a run of column rows, drawn fixed-width so the server's own spacing lines them up again
export const renderCols = lines => `<div class="tx-cols">${lines.map(l => `<div>${meters(l.html)}</div>`).join('')}</div>`;
// (an indented line amid them is one of them, its fields one space apart: "  manabound_gryphon A ...")
export const inList = text => /^\s+\S/.test(text);

// the prompt a line can begin with ("20/20hp 128/128mp 158/158mv> the pilgrim leaves north"): the
// HUD shows those numbers itself, so it goes, and the rest of the line stays
export const PROMPT_AT = /^\s*<?\s*\d+\/\d+\s*hp\b[^>\n]*>\s*/i;
export function unprompt(html) {
  // (each entity one character, as it shows)
  const plain = String(html).replace(/<[^>]*>/g, '').replace(/&(gt|lt|amp|quot|#\d+);/g, (_, e) => ({ gt: '>', lt: '<', amp: '&', quot: '"' }[e] || '?'));
  const m = plain.match(PROMPT_AT);
  if (!m) return html;
  let drop = m[0].length;
  return String(html).split(/(<[^>]*>)/).map(p => {
    if (!drop || p.startsWith('<')) return p;
    let i = 0;
    while (i < p.length && drop) { i = p[i] === '&' && p.indexOf(';', i) > i ? p.indexOf(';', i) + 1 : i + 1; drop--; }
    return p.slice(i);
  }).join('');
}

// a line between two rules that is a title: short, and not a sentence ("No players found." is not)
export const isTitle = text => { const t = String(text).trim(); return t.length > 0 && t.length <= 60 && !/[.!?]$/.test(t); };

// is this line part of a framed block (a box's rule or row)?
export const framed = text => { const k = classify(text).t; return k === 'rule' || k === 'row'; };

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// the html of a box's row without its outer bars: the first and the last bar of its text go
// (inner ones stay, as faint column marks), tags untouched
function unbar(html) {
  const parts = String(html).split(/(<[^>]*>)/);
  const spots = [];
  parts.forEach((p, i) => { if (p.startsWith('<')) return; for (let j = 0; j < p.length; j++) if (BAR.test(p[j])) spots.push([i, j]); });
  if (!spots.length) return html;
  const drop = [spots[0]];
  if (spots.length > 1) {
    const [li, lj] = spots[spots.length - 1];
    // the closing bar: only if nothing but spaces follows it
    const rest = parts.slice(li + 1).filter(p => !p.startsWith('<')).join('') + parts[li].slice(lj + 1);
    if (!rest.trim()) drop.push([li, lj]);
  }
  for (const [i, j] of drop.sort((a, b) => b[0] - a[0] || b[1] - a[1])) parts[i] = parts[i].slice(0, j) + parts[i].slice(j + 1);
  // the bars left inside are a table's columns: drawn faint
  return meters(parts.map(p => (p.startsWith('<') ? p : p.replace(/[║│|]/g, '<span class="tx-bar">$&</span>'))).join(''));
}

// a telnet progress bar, "[█████░░░░░]" (its colours' tags in it or not), drawn as a meter of the
// same width, so the columns after it stay in step
const METER = /\[((?:<[^>]*>|[█▓▒░■□▮▯ ])+)\]/g;
// (or without brackets: a run of six or more, "Rage: ░░░░░░░░░░ 0/100")
const BARE = /((?:<[^>]*>)*[█▓▒░■□▮▯](?:(?:<[^>]*>)*[█▓▒░■□▮▯]){5,}(?:<[^>]*>)*)/g;
const meter = (cells, extra) => {
  const full = (cells.match(/[█▓■▮]/g) || []).length;
  return `<span class="tx-meter" style="width:${cells.length + extra}ch"><i style="width:${Math.round(full / cells.length * 100)}%"></i></span>`;
};
export function meters(html) {
  return String(html).replace(METER, (all, inner) => {
    const cells = inner.replace(/<[^>]*>/g, '');
    if (cells.length < 4 || !/[█▓▒░■□▮▯]/.test(cells)) return all;
    return meter(cells, 2);
  }).replace(BARE, all => meter(all.replace(/<[^>]*>/g, ''), 0));
}

// the html of a block of framed lines (rules and rows), as a banner or a panel
export function renderBox(lines) {
  const items = lines.map(l => ({ ...l, k: classify(l.text) }));
  const rows = items.filter(i => i.k.t === 'row');
  const filled = rows.filter(r => r.k.text.trim());
  // a banner: a title or two in a little box, no columns
  const small = filled.length && filled.length <= 3 && filled.every(r => r.k.text.trim().length <= 60 && !BAR.test(r.k.text));
  if (small) {
    // (a journal's *NPC* / *LORE* tag, and stars, are the telnet's ornament)
    const [head, ...more] = filled.map(r => r.k.text.trim().replace(/^\*[A-Z]+\*\s*/, '').replace(/^[★☆✦✧•*\s]+|[★☆✦✧•*\s]+$/g, ''));
    return `<div class="tx-banner"><div class="tx-banner-t">${esc(head)}</div>${more.map(m => `<div class="tx-banner-s">${esc(m)}</div>`).join('')}</div>`;
  }
  if (!rows.length) return '<div class="tx-rule"></div>';
  // a panel: the rows in step, inner rules as hairlines, the frame its own border
  let out = '', first = true;
  for (const i of items) {
    if (i.k.t === 'rule') { if (!first && i !== items[items.length - 1]) out += '<div class="tx-sep"></div>'; continue; }
    first = false;
    out += `<div class="tx-row">${unbar(i.html) || '&nbsp;'}</div>`;
  }
  return `<div class="tx-panel">${out.replace(/(<div class="tx-sep"><\/div>)+$/, '')}</div>`;
}

// one line that is not in a box: a rule, a heading on a rule, or the line itself
export function renderLine(line) {
  const k = classify(line.text);
  if (k.t === 'rule') return '<div class="tx-rule"></div>';
  if (k.t === 'titled') return `<div class="tx-head">${esc(k.title)}</div>`;
  return null;
}

// a whole reply at once (the talk window, help): [{html, cls}] for each block or line, boxes
// gathered, a title between two rules made a heading
export function formatLines(lines) {
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i], k = classify(l.text);
    if (k.t === 'row' || (k.t === 'rule' && i + 1 < lines.length && classify(lines[i + 1].text).t === 'row')) {
      const box = [l];
      while (i + 1 < lines.length && framed(lines[i + 1].text)) box.push(lines[++i]);
      out.push({ html: renderBox(box), box: true });
      continue;
    }
    // a short line between two rules: a heading (help's "=====\nTITLE\n=====")
    if (k.t === 'rule' && i + 2 < lines.length && classify(lines[i + 1].text).t === 'text'
        && classify(lines[i + 2].text).t === 'rule' && isTitle(lines[i + 1].text)) {
      out.push({ html: `<div class="tx-head">${esc(lines[i + 1].text.trim())}</div>`, box: true });
      i += 2;
      continue;
    }
    if (k.t === 'cols') {
      const run = [l];
      // (as the chat log gathers them: an indented line goes on the run)
      const next = j => j < lines.length && (classify(lines[j].text).t === 'cols' || (inList(lines[j].text) && classify(lines[j].text).t === 'text'));
      while (next(i + 1)) run.push(lines[++i]);
      out.push({ html: renderCols(run), box: true });
      continue;
    }
    const one = renderLine(l);
    if (one) { if (!(one.includes('tx-rule') && out.length && out[out.length - 1].html.includes('tx-rule'))) out.push({ html: one, box: true }); continue; }
    if (k.t === 'blank') continue;
    out.push({ html: meters(l.html), text: l.text, box: false });
  }
  return out;
}

// what a line of a reply is for the talk window: the person's words, or a note of what happened
// to you (a reward, a quest step), drawn apart from them
export function noteKind(text) {
  const t = String(text || '').trim();
  if (/^You (gain|receive|earn|learn|are awarded)\b|^\+\d+ |experience!$|gold!$/i.test(t)) return 'reward';
  if (/^(Quest (accepted|progress|complete|updated)|Objective complete|Tutorial step|New objective|Tutorial step complete|You have completed)/i.test(t)) return 'quest';
  if (/^New in your journal\b/i.test(t)) return 'journal';
  return '';
}
