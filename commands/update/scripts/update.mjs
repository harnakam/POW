#!/usr/bin/env node
// Standalone Node 20+ workflow evidence store. Discovery never loads repository code.
import { createHash, randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { lstat, readdir, readFile, realpath, mkdir, open, rename, unlink } from 'node:fs/promises';
import path from 'node:path';

const VERSION = 1;
const LIMIT = { files: 2000, fileBytes: 1048576, totalBytes: 33554432, output: 1048576, workflows: 50, sequences: 20, steps: 20, outcomes: 50, history: 50 };
const TTL = 7 * 86400000;
const EXCLUDE = new Set(['.git', '.pow', 'node_modules', 'dist', 'build', 'coverage', '.next', '.venv', '__pycache__']);
const digest = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
const now = () => new Date().toISOString();
const secretPath = value => /(^|\/)(\.env(?:\..*)?|credentials(?:\..*)?|id_rsa|id_ed25519|.*\.(?:pem|key|p12))$/i.test(value);
const remote = value => /(?:publish|deploy|release|push|upload|destroy|delete|clean|install|migration|migrate)/i.test(value);
class UpdateError extends Error {}
const fail = message => { throw new UpdateError(message); };
const inside = (root, file) => { const relative = path.relative(root, file); return !relative.startsWith('..') && !path.isAbsolute(relative); };

async function safeFile(root, relative) {
  const absolute = path.resolve(root, relative);
  if (!inside(root, absolute)) fail('Path escapes root.');
  let cursor = root;
  for (const part of path.relative(root, absolute).split(path.sep).filter(Boolean)) {
    cursor = path.join(cursor, part);
    try { if ((await lstat(cursor)).isSymbolicLink()) fail('Symlink paths are unsupported.'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return absolute;
}

async function execute(executable, args, root, timeout = 10000, capture = true) {
  return new Promise(resolve => {
    const env = { ...process.env, GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0', GIT_PAGER: 'cat' };
    delete env.NODE_OPTIONS;
    delete env.NODE_PATH;
    let child;
    try { child = spawn(executable, args, { cwd: root, shell: false, windowsHide: true, detached: process.platform !== 'win32', env, stdio: ['ignore', 'pipe', 'pipe'] }); }
    catch { resolve({ code: null, error: 'spawn', bytes: 0, text: '' }); return; }
    let text = '', bytes = 0, error = null, ended = false;
    const hash = createHash('sha256');
    const finish = code => { if (ended) return; ended = true; clearTimeout(timer); clearTimeout(grace); resolve({ code, error, bytes, outputHash: hash.digest('hex'), text }); };
    const stop = reason => {
      if (error) return;
      error = reason;
      if (child.pid && process.platform === 'win32') {
        // A Windows .cmd wrapper is never invoked. Kill only this owned process tree.
        const killer = spawn(path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'taskkill.exe'), ['/PID', String(child.pid), '/T', '/F'], { shell: false, windowsHide: true, stdio: 'ignore' });
        killer.on('error', () => child.kill());
        const killTimer = setTimeout(() => { killer.kill(); child.kill(); }, 2000);
        killer.on('close', () => clearTimeout(killTimer));
      } else { try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); } }
      grace = setTimeout(() => { child.stdout.destroy(); child.stderr.destroy(); finish(null); }, 3000);
    };
    const collect = chunk => {
      bytes += chunk.length;
      if (bytes > LIMIT.output) { stop('output-limit'); return; }
      hash.update(chunk);
      if (capture) text += chunk.toString('utf8');
    };
    let grace;
    const timer = setTimeout(() => stop('timeout'), timeout);
    child.stdout.on('data', collect);
    child.stderr.on('data', collect);
    child.on('error', () => { error = 'spawn'; finish(null); });
    child.on('close', code => finish(code));
  });
}

async function discover(root) {
  const sources = [], bodies = new Map(), limitations = [];
  let bytes = 0, visited = 0, incomplete = false;
  async function walk(relative = '', depth = 0) {
    if (depth > 12) { incomplete = true; return; }
    const entries = (await readdir(path.join(root, relative), { withFileTypes: true })).sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (++visited > LIMIT.files) { incomplete = true; return; }
      const name = relative ? `${relative}/${entry.name}` : entry.name;
      if (EXCLUDE.has(entry.name) || secretPath(name)) continue;
      if (entry.isSymbolicLink()) { incomplete = true; continue; }
      if (entry.isDirectory()) { await walk(name, depth + 1); continue; }
      if (!entry.isFile()) continue;
      const file = await safeFile(root, name);
      const info = await lstat(file);
      if (info.size > LIMIT.fileBytes || bytes + info.size > LIMIT.totalBytes) { incomplete = true; continue; }
      const content = await readFile(file);
      bytes += content.length;
      sources.push([name, digest(content)]);
      if (name === 'package.json' || /^\.github\/workflows\/[^/]+\.ya?ml$/.test(name)) bodies.set(name, content.toString('utf8'));
    }
  }
  await walk();
  sources.sort((a, b) => a[0].localeCompare(b[0]));
  const gitBase = ['--no-pager', '-c', 'core.fsmonitor=false'];
  // Fixed read-only argv; never inspect commit messages, patches, remotes, or shell history.
  const history = await execute('git', [...gitBase, 'log', `-${LIMIT.history}`, '--format=', '--name-only', '--no-renames', '--no-ext-diff', '--', '.'], root);
  const head = await execute('git', [...gitBase, 'rev-parse', '--verify', 'HEAD'], root);
  const counts = new Map();
  if (history.code === 0 && !history.error) for (const name of history.text.split(/\r?\n/).filter(Boolean)) counts.set(name, (counts.get(name) || 0) + 1);
  else limitations.push('Git history unavailable; repetition evidence is incomplete.');
  const ci = [...bodies].filter(([name]) => name.startsWith('.github/'));
  let scripts = {};
  if (bodies.has('package.json')) {
    try { scripts = JSON.parse(bodies.get('package.json')).scripts || {}; }
    catch { limitations.push('package.json is invalid; no package workflows inferred.'); }
  }
  const workflows = [];
  for (const [name, command] of Object.entries(scripts).sort(([a], [b]) => a.localeCompare(b))) {
    if (workflows.length >= LIMIT.workflows) { limitations.push('Workflow limit reached.'); break; }
    if (!/^[a-zA-Z0-9:_-]{1,64}$/.test(name) || typeof command !== 'string') continue;
    const argv = command.trim().split(/\s+/);
    // Deliberately narrow portable subset: no quoting, interpolation, inline JS or Node loader flags.
    let reason = 'Only simple node relative-script argv is runnable; review shell/lifecycle steps manually.';
    let step = null;
    if (argv[0] === 'node' && /^(?:[a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_-]+\.(?:mjs|cjs|js)$/.test(argv[1] || '') && argv.slice(2).every(arg => /^(?:--check|--noEmit|--verbose|[a-zA-Z0-9_-]{1,40})$/.test(arg))) {
      if (sources.some(([file]) => file === argv[1])) { step = argv.slice(1); reason = null; }
      else reason = 'Node entry point was not safely fingerprinted.';
    }
    if (remote(name) || remote(command)) { step = null; reason = 'Potential external/destructive operation; separate explicit authorization and manual execution required.'; }
    if (scripts[`pre${name}`] || scripts[`post${name}`]) { step = null; reason = 'npm lifecycle hooks present; direct Node execution would change semantics.'; }
    const ciFiles = ci.filter(([, body]) => body.includes(`npm run ${name}`) || (name === 'test' && /\bnpm test\b/.test(body))).map(([file]) => file);
    workflows.push({ id: `package:${name}`, name, commandHash: digest(command), step, manualReason: reason,
      evidence: { package: 'package.json', ciFiles, historyTouches: counts.get(argv[1]) || counts.get('package.json') || 0 },
      judgment: 'Candidate inferred from current package declaration; history touches and CI references do not prove execution or permission.' });
  }
  if (incomplete) limitations.push('Discovery bounds or symlinks prevented a complete fingerprint; execution disabled.');
  const sequences = [];
  for (const [file, body] of ci) {
    let inJobs = false, current = null, stepsIndent = null;
    for (const [offset, line] of body.split(/\r?\n/).entries()) {
      if (/^jobs:\s*(?:#.*)?$/.test(line)) { inJobs = true; continue; }
      if (/^[^\s#]/.test(line)) { inJobs = false; current = null; }
      if (!inJobs) continue;
      const job = /^  ([a-zA-Z0-9_-]{1,64}):\s*(?:#.*)?$/.exec(line);
      if (job) {
        current = null;
        stepsIndent = null;
        if (sequences.length >= LIMIT.sequences) { limitations.push('CI sequence limit reached.'); continue; }
        current = { id: `ci:${file}:${job[1]}`, source: { file, line: offset + 1, job: job[1] }, basis: 'inferred-ci-declaration',
          judgment: 'Listed run declarations within one job, not observed execution. Conditions, matrices, needs, actions and shell semantics require review; no cross-job order is inferred.', steps: [] };
        sequences.push(current);
        continue;
      }
      const steps = /^(\s+)steps:\s*(?:#.*)?$/.exec(line);
      if (steps && current) { stepsIndent = steps[1].length; continue; }
      if (stepsIndent !== null && line.trim() && !line.trimStart().startsWith('#') && line.search(/\S/) <= stepsIndent) stepsIndent = null;
      const declarationLine = /^(\s*)(-\s+)?(run|uses):\s*(.*?)\s*$/.exec(line);
      if (!current || stepsIndent === null || !declarationLine) continue;
      if (declarationLine[1].length !== stepsIndent + (declarationLine[2] ? 2 : 4)) continue;
      if (current.steps.length >= LIMIT.steps) { if (!current.truncated) limitations.push('CI job step limit reached; sequence is partial.'); current.truncated = true; continue; }
      const declaration = declarationLine[4], action = declarationLine[3] === 'uses';
      const packageRun = /^(?:npm run ([a-zA-Z0-9:_-]{1,64})|npm (test))$/.exec(declaration);
      const candidate = action ? null : packageRun ? workflows.find(item => item.name === (packageRun[1] || packageRun[2])) : workflows.find(item => scripts[item.name]?.trim() === declaration);
      const block = !declaration || /^[|>]/.test(declaration);
      current.steps.push({ position: current.steps.length + 1, source: { file, line: offset + 1 }, declarationHash: digest(declaration), workflowId: candidate?.id || null,
        kind: !block && candidate?.step ? 'review-local-step' : 'manual',
        manualReason: action ? 'CI action semantics and effects are unresolved; inspect source and inputs manually.' : block ? 'Multiline or empty shell declaration; inspect source manually.' : candidate?.manualReason || (!candidate ? 'Unmapped CI shell/action; inspect source manually, with separate authorization for external effects.' : null) });
    }
  }
  const headId = head.code === 0 && /^[0-9a-f]{40,64}\s*$/.test(head.text) ? head.text.trim() : null;
  const fingerprint = digest({ sources, head: headId, runtime: process.version, platform: process.platform });
  return { fingerprint, complete: !incomplete, sources, head: headId, workflows, sequences: sequences.filter(item => item.steps.length > 0), limitations, history: { commitsLimit: LIMIT.history, available: history.code === 0 && !history.error } };
}

async function readState(root) {
  const file = await safeFile(root, '.pow/update/state.json');
  try {
    if ((await lstat(file)).size > LIMIT.fileBytes) fail('State exceeds size limit.');
    const state = JSON.parse(await readFile(file, 'utf8'));
    if (state.schemaVersion !== VERSION || state.rootHash !== digest(root) || !Number.isSafeInteger(state.revision) || !Array.isArray(state.workflows) || !Array.isArray(state.outcomes) || state.workflows.length > LIMIT.workflows || state.outcomes.length > LIMIT.outcomes || !Number.isFinite(Date.parse(state.scannedAt))) fail('Unsupported or invalid state; preserve it and review before resetting.');
    return state;
  } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

async function locked(root, callback) {
  const dir = await safeFile(root, '.pow/update');
  await mkdir(dir, { recursive: true });
  const lockPath = await safeFile(root, '.pow/update/lock');
  let lock;
  try { lock = await open(lockPath, 'wx', 0o600); }
  catch (error) { if (error.code === 'EEXIST') fail('Update is locked. If its owner exited, inspect and remove .pow/update/lock manually.'); throw error; }
  try { await lock.writeFile(JSON.stringify({ pid: process.pid, at: now() })); return await callback(); }
  finally { await lock.close(); await unlink(lockPath); }
}

async function save(root, state) {
  const file = await safeFile(root, '.pow/update/state.json');
  const temporary = await safeFile(root, `.pow/update/state-${randomUUID()}.tmp`);
  const handle = await open(temporary, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(state, null, 2)}\n`); await handle.sync(); }
  finally { await handle.close(); }
  try { await rename(temporary, file); }
  catch (error) { await unlink(temporary); throw error; }
}

function snapshot(root, scan, previous) {
  return { schemaVersion: VERSION, rootHash: digest(root), revision: (previous?.revision || 0) + 1, scannedAt: now(), fingerprint: scan.fingerprint,
    complete: scan.complete, sources: scan.sources, head: scan.head, history: scan.history, limitations: scan.limitations,
    workflows: scan.workflows.map(({ step, judgment, ...workflow }) => ({ ...workflow, runnable: Boolean(step) })),
    sequences: scan.sequences,
    outcomes: (previous?.outcomes || []).filter(item => Date.now() - Date.parse(item.at) < 90 * 86400000).slice(-LIMIT.outcomes) };
}

function plan(root, scan, state, timeout) {
  const fresh = Boolean(state && state.fingerprint === scan.fingerprint && Date.now() - Date.parse(state.scannedAt) < TTL);
  const workflows = scan.workflows.map(workflow => {
    const last = state?.outcomes.filter(item => item.workflow === workflow.id).at(-1);
    const observations = state?.outcomes.filter(item => item.workflow === workflow.id && item.fingerprint === scan.fingerprint) || [];
    const status = !fresh ? 'stale' : !workflow.step || !scan.complete ? 'manual' : last && last.status !== 'success' ? 'review-failure' : observations.some(item => item.status === 'success') ? 'observed-success' : 'untried';
    const approval = fresh && workflow.step && scan.complete ? digest({ root, fingerprint: scan.fingerprint, workflow: workflow.id, step: workflow.step, revision: state.revision, timeout }) : null;
    return { ...workflow, argv: workflow.step ? [process.execPath, ...workflow.step] : null, status, observations: { successes: observations.filter(item => item.status === 'success').length, failures: observations.filter(item => item.status !== 'success').length, last: last || null }, approval };
  });
  const sequences = scan.sequences.map(sequence => ({ ...sequence, status: fresh ? 'review-sequence' : 'stale', executable: false,
    steps: sequence.steps.map(step => {
      const candidate = workflows.find(item => item.id === step.workflowId);
      return { ...step, argv: step.kind === 'review-local-step' ? candidate?.argv || null : null, localStatus: candidate?.status || null };
    }) }));
  return { schemaVersion: VERSION, fingerprint: scan.fingerprint, fresh, revision: state?.revision || 0, complete: scan.complete, timeoutMs: timeout, limitations: scan.limitations, workflows, sequences };
}

async function main() {
  if (Number(process.versions.node.split('.')[0]) < 20) fail('Node 20+ required.');
  const args = process.argv.slice(2), command = args.shift();
  if (!command || command === '--help') {
    console.log('update scan|plan|run --root PATH [--write] [--workflow package:NAME --approve SHA256] [--timeout-ms 1..60000]\nscan is read-only unless --write; plan is read-only; run requires a fresh persisted scan and explicit approval of its plan.'); return;
  }
  if (!['scan', 'plan', 'run'].includes(command)) fail('Unknown command.');
  const options = {};
  while (args.length) {
    const flag = args.shift();
    if (!['--root', '--write', '--workflow', '--approve', '--timeout-ms'].includes(flag) || options[flag] !== undefined) fail('Unknown or duplicate option.');
    if (flag === '--write') options[flag] = true;
    else { const value = args.shift(); if (!value || value.startsWith('--')) fail('Option requires a value.'); options[flag] = value; }
  }
  if (options['--write'] && command !== 'scan') fail('--write is only valid for scan.');
  if ((options['--workflow'] || options['--approve']) && command !== 'run') fail('Execution options are only valid for run.');
  const root = await realpath(path.resolve(options['--root'] || process.cwd()));
  const timeout = Number(options['--timeout-ms'] || 30000);
  if (!Number.isInteger(timeout) || timeout < 1 || timeout > 60000) fail('Timeout must be an integer from 1 to 60000 ms.');
  const action = async () => {
    const state = await readState(root);
    const scan = await discover(root);
    if (command === 'scan') {
      const learned = snapshot(root, scan, state);
      if (options['--write']) await save(root, learned);
      return { written: Boolean(options['--write']), state: learned, plan: plan(root, scan, options['--write'] ? learned : state, timeout) };
    }
    const reviewed = plan(root, scan, state, timeout);
    if (command === 'plan') return reviewed;
    const workflow = reviewed.workflows.find(item => item.id === options['--workflow']);
    if (!workflow || !workflow.approval || workflow.approval !== options['--approve']) fail('Execution refused: select a runnable workflow and explicitly approve its current fresh plan token.');
    // Consume authorization before launching. A crash leaves an inspectable interrupted outcome.
    const outcome = { id: randomUUID(), at: now(), workflow: workflow.id, fingerprint: scan.fingerprint, status: 'interrupted', timeoutMs: timeout };
    state.revision++;
    state.outcomes = [...state.outcomes, outcome].slice(-LIMIT.outcomes);
    await save(root, state);
    const started = Date.now();
    const result = await execute(process.execPath, workflow.step, root, timeout, false);
    Object.assign(outcome, { status: result.error || (result.code === 0 ? 'success' : 'exit-failure'), exitCode: result.code, durationMs: Date.now() - started, outputBytes: result.bytes, outputHash: result.outputHash || null });
    state.revision++;
    await save(root, state);
    if (outcome.status !== 'success') process.exitCode = 1;
    return { outcome, next: 'Review failures or changed inputs, then request a new plan. Output content is deliberately not retained.' };
  };
  console.log(JSON.stringify(command === 'run' || options['--write'] ? await locked(root, action) : await action(), null, 2));
}

main().catch(error => {
  // Filesystem/process exceptions can contain paths or command contents; do not echo them.
  console.error(JSON.stringify({ error: error instanceof UpdateError ? error.message : 'Update failed reading files, state, or processes. Inspect the root and state without exposing secrets; no automatic retry.' }));
  process.exitCode = 1;
});
