// Make a model with Tripo's API (developers.tripo3d.ai, v3): concept images from a prompt, then
// the chosen concept turned into a low-poly textured model. What to make is a spec in tripo/
// (committed, so every asset can be traced and made again); what comes back goes to
// .cache/tripo/<name>/ with run.json, the log of every task and the credits it took. The model the
// kit is built from is kept beside its spec (tripo/<name>.glb, with that log as <name>.run.json),
// so a fresh clone builds the same piece without asking Tripo again.
//   node tripo.mjs balance
//   node tripo.mjs concepts tripo/<name>.json               -> concept_1.png ... (spec.concepts of them)
//   node tripo.mjs model tripo/<name>.json --concept N      -> model.glb, model_preview.png; tripo/<name>.glb
// The key is TRIPO_API_KEY, from the environment or (on Windows, for a shell started before it
// was set) the user's environment in the registry. It is never printed.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const API = 'https://openapi.tripo3d.ai/v3';

function apiKey() {
  let k = process.env.TRIPO_API_KEY;
  if (!k && process.platform === 'win32') {
    try {
      k = execFileSync('powershell', ['-NoProfile', '-Command', "[Environment]::GetEnvironmentVariable('TRIPO_API_KEY','User')"],
        { encoding: 'utf8' }).trim();
    } catch { /* no PowerShell: fall through */ }
  }
  if (!k) throw new Error('TRIPO_API_KEY is not set');
  return k;
}
const KEY = apiKey();

async function call(method, route, body) {
  for (let tries = 0; ; tries++) {
    const r = await fetch(API + route, {
      method,
      headers: { Authorization: `Bearer ${KEY}`, 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    const j = await r.json().catch(() => ({ code: r.status, message: r.statusText }));
    if (j.code === 0) return j.data;
    // 2000: over the account's limit of tasks at once; wait as long as it asks and go again
    if (j.code === 2000 && tries < 40) {
      const wait = Math.max(5, Number(r.headers.get('retry-after')) || 15);
      process.stdout.write(`
(over Tripo's limit of tasks at once: trying again in ${wait} s)   `);
      await new Promise(res => setTimeout(res, wait * 1000));
      continue;
    }
    throw new Error(`${method} ${route}: ${j.code} ${j.message || ''}${j.suggestion ? ` (${j.suggestion})` : ''}`);
  }
}

// a task to its end: its final record, or an error if it failed
async function run(route, body, label, started = () => {}) {
  const { task_id } = await call('POST', route, body);
  started(task_id);
  const t0 = Date.now();
  for (;;) {
    await new Promise(r => setTimeout(r, 3000));
    const t = await call('GET', `/tasks/${task_id}`);
    process.stdout.write(`\r${label}: ${t.status} ${t.progress ?? 0}%   `);
    if (t.status === 'success') { process.stdout.write('\n'); return t; }
    if (['failed', 'cancelled'].includes(t.status)) throw new Error(`\n${label}: ${t.status} ${t.error_code || ''} ${t.error_message || ''}`);
    if (Date.now() - t0 > 15 * 60e3) throw new Error(`\n${label}: still ${t.status} after 15 minutes (task ${task_id})`);
  }
}

async function download(url, file) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`download ${file}: ${r.status}`);
  fs.writeFileSync(file, Buffer.from(await r.arrayBuffer()));
  return file;
}

const [cmd, specFile] = process.argv.slice(2);
const opt = name => { const i = process.argv.indexOf(`--${name}`); return i > 0 ? process.argv[i + 1] : null; };

if (cmd === 'balance') {
  console.log(await call('GET', '/account/balance'));
  process.exit(0);
}
if (!['concepts', 'model'].includes(cmd) || !specFile) {
  console.error('usage: node tripo.mjs balance | concepts <spec.json> | model <spec.json> --concept N');
  process.exit(2);
}
const spec = JSON.parse(fs.readFileSync(path.resolve(specFile), 'utf8'));
const dir = path.join(HERE, '.cache', 'tripo', spec.name);
fs.mkdirSync(dir, { recursive: true });
const logFile = path.join(dir, 'run.json');
const log = fs.existsSync(logFile) ? JSON.parse(fs.readFileSync(logFile, 'utf8')) : { name: spec.name, concepts: [], models: [] };
const save = () => fs.writeFileSync(logFile, JSON.stringify(log, null, 1));

if (cmd === 'concepts') {
  // one at a time: an account may run only so many tasks at once
  for (let i = 0; i < (spec.concepts || 1); i++) {
    const n = log.concepts.length + 1;
    const t = await run('/generation/text-to-image', spec.image, `concept ${n}`, id => { log.pending = id; save(); });
    delete log.pending;
    const file = await download(t.output.generated_image_url, path.join(dir, `concept_${n}.png`));
    log.concepts.push({ n, task_id: t.task_id, credits: t.credits_consumed, file: path.basename(file), spec: spec.image, at: t.completed_at });
    console.log(`concept ${n}: ${file} (${t.credits_consumed} credits)`);
  }
  save();
} else {
  const n = Number(opt('concept'));
  const c = log.concepts.find(x => x.n === n);
  if (!c) throw new Error(`no concept ${opt('concept')}: run 'concepts' first (have ${log.concepts.map(x => x.n).join(', ') || 'none'})`);
  const t = await run('/generation/image-to-model', { ...spec.model, input: c.task_id }, `model from concept ${n}`, id => { log.pending = id; save(); });
  delete log.pending;
  const url = t.output.model_url || t.output.pbr_model_url || t.output.base_model_url;
  if (!url) throw new Error(`model: no model in the task's output (${Object.keys(t.output).join(', ')})`);
  const file = await download(url, path.join(dir, 'model.glb'));
  if (t.output.rendered_image_url) await download(t.output.rendered_image_url, path.join(dir, 'model_preview.png'));
  log.models.push({ concept: n, task_id: t.task_id, credits: t.credits_consumed, file: path.basename(file), spec: spec.model, at: t.completed_at });
  save();
  fs.copyFileSync(file, path.join(HERE, 'tripo', `${spec.name}.glb`));
  fs.copyFileSync(logFile, path.join(HERE, 'tripo', `${spec.name}.run.json`));
  console.log(`model: ${file} (${t.credits_consumed} credits), kept as tripo/${spec.name}.glb`);
}
