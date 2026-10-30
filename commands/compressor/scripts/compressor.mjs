#!/usr/bin/env node
// Node 20+, standard library only. Plans are review records, never executable code.
import * as fs from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const STATE = '.pow/compressor';
const hash = data => createHash('sha256').update(data).digest('hex');
const json = value => JSON.stringify(value, null, 2) + '\n';
const fail = message => { throw new Error(message); };
const inside = (root, target) => { const rel = path.relative(root, target); return rel !== '..' && !rel.startsWith('..' + path.sep) && !path.isAbsolute(rel); };
const doc = p => /\.(md|mdx|rst|txt)$/i.test(p);
const source = p => /\.(m?[jt]sx?|cjs|py|go|rs|java|cs|rb|php)$/i.test(p);
const test = p => /(^|\/)(__tests__|tests?|specs?)(\/|\.)|[._-](test|spec)\./i.test(p);
const sensitive = p => /(^|\/)(\.env(?:\..*)?|.*\.(pem|key|p12)|id_rsa|credentials|secrets?)(\/|$)/i.test(p);
const protectedName = p => sensitive(p) || /(^|\/)(licen[cs]e[^/]*|copying[^/]*|notice[^/]*|package(?:-lock)?\.json|.*config[^/]*|.*\.lock|AGENTS\.md|SKILL\.md|\.gitignore)$/i.test(p);
const excluded = p => { const folded = p.toLowerCase(); return folded === '.git' || folded.startsWith('.git/') || folded === STATE || folded.startsWith(STATE + '/'); };
function relative(p) {
  if (typeof p !== 'string' || !p || p.includes('\\') || p.includes(':') || p.includes('\0') || path.posix.isAbsolute(p) || p.split('/').some(x => !x || x === '.' || x === '..' || /[. ]$/.test(x))) fail(`Unsafe relative path: ${p}`);
  if (p.split('/').some(x => /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(x))) fail(`Reserved path: ${p}`);
  return p;
}
async function safe(root, rel, missing = false) {
  relative(rel);
  let current = root;
  for (const part of rel.split('/')) {
    const names = await fs.readdir(current).catch(e => e.code === 'ENOENT' && missing ? [] : Promise.reject(e));
    const variants = names.filter(n => n.toLowerCase() === part.toLowerCase());
    if (variants.length > 1 || (variants.length === 1 && variants[0] !== part)) fail(`Case alias: ${rel}`);
    current = path.join(current, part);
    const st = await fs.lstat(current).catch(e => e.code === 'ENOENT' && missing ? null : Promise.reject(e));
    if (!st) continue;
    if (st.isSymbolicLink()) fail(`Link/junction rejected: ${rel}`);
    const real = await fs.realpath(current);
    if (!inside(root, real)) fail(`Escaped root: ${rel}`);
  }
  return current;
}
async function identity(root) {
  const st = await fs.stat(root);
  return { realpath: root, device: String(st.dev), inode: String(st.ino) };
}
function git(root, args) {
  // Discovery must not execute repository-configured fsmonitor or diff helpers.
  return execFileSync('git', ['--no-pager', '-c', 'core.fsmonitor=false', '-C', root, ...args], { encoding: 'utf8', timeout: 10000, maxBuffer: 32 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, GIT_OPTIONAL_LOCKS: '0' } });
}
function gitState(root) {
  try {
    const prefix = git(root, ['rev-parse', '--show-prefix']).trim();
    if (prefix) fail('Choose the Git working-tree root, not a subdirectory.');
    const tracked = new Set(), indexFlags = new Set();
    for (const record of git(root, ['ls-files', '-v', '-z']).split('\0').filter(Boolean)) {
      const tag = record[0], p = record.slice(2);
      tracked.add(p);
      // H is ordinary; lowercase tags mean assume-unchanged. S/s denotes skip-worktree.
      // Every nonordinary index state needs explicit selection, even if diff is empty.
      if (tag !== 'H') indexFlags.add(p);
    }
    const dirty = new Set();
    for (const args of [['diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z'], ['diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-only', '-z']]) {
      for (const p of git(root, args).split('\0').filter(Boolean)) dirty.add(p);
    }
    return { tracked, dirty, indexFlags, available: true };
  } catch (e) {
    if (e.message.startsWith('Choose the Git')) throw e;
    return { tracked: new Set(), dirty: new Set(), indexFlags: new Set(), available: false };
  }
}
async function inventory(root) {
  const files = [], skipped = [], state = gitState(root);
  async function walk(dir = '') {
    const entries = await fs.readdir(path.join(root, dir), { withFileTypes: true });
    const folded = new Set();
    for (const ent of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      const rel = dir ? dir + '/' + ent.name : ent.name;
      if (folded.has(ent.name.toLowerCase())) fail(`Case-folding collision: ${rel}`);
      folded.add(ent.name.toLowerCase());
      if (excluded(rel)) continue;
      relative(rel);
      if (ent.isSymbolicLink()) { skipped.push({ path: rel, reason: 'link/junction' }); continue; }
      if (ent.isDirectory()) {
        if (['node_modules', '.venv', 'venv', '.hg', '.svn'].includes(ent.name)) { skipped.push({ path: rel, reason: 'dependency or VCS directory' }); continue; }
        await safe(root, rel);
        await walk(rel);
      } else if (ent.isFile()) {
        const full = await safe(root, rel);
        const st = await fs.lstat(full);
        if (st.size > 2 * 1024 * 1024) { skipped.push({ path: rel, reason: 'over 2 MiB inspection limit' }); continue; }
        const bytes = await fs.readFile(full);
        const protection = [];
        if (!state.available) protection.push('git status unavailable');
        else if (!state.tracked.has(rel)) protection.push('untracked/ignored');
        if (state.dirty.has(rel)) protection.push('dirty/index change');
        if (state.indexFlags.has(rel)) protection.push('nonordinary index flags (including skip-worktree/assume-unchanged)');
        if (protectedName(rel)) protection.push('license/secret/config/instructions');
        if (st.nlink > 1) protection.push('hard linked');
        const text = !sensitive(rel) && !bytes.includes(0) ? bytes.toString('utf8') : null;
        files.push({ path: rel, sha256: hash(bytes), bytes: bytes.length, mode: st.mode, test: test(rel), protection, text });
      } else skipped.push({ path: rel, reason: 'non-regular file' });
    }
  }
  await walk();
  return { files, skipped, gitAvailable: state.available };
}
function findings(files) {
  const byPath = new Map(files.map(f => [f.path, f]));
  const refs = new Map(files.map(f => [f.path, []]));
  const unresolved = [];
  for (const f of files) {
    if (f.text === null) continue;
    for (const [i, line] of f.text.split('\n').entries()) {
      // Literal imports, require/import calls, Markdown links, and literal path strings.
      const pattern = /(?:from\s*|import\s*\(?\s*|require\s*\(\s*)["']([^"']+)["']|\]\(([^)\s]+)\)|["']((?:\.?\.\/)?[\w@./-]+\.[\w]+)["']/g;
      for (const m of line.matchAll(pattern)) {
        const spec = (m[1] || m[2] || m[3]).split('#')[0];
        if (!spec || /^(https?:|mailto:|data:|node:|\/\/)/.test(spec)) continue;
        let decoded;
        try { decoded = decodeURIComponent(spec); } catch { continue; }
        const base = path.posix.normalize(path.posix.join(path.posix.dirname(f.path), decoded));
        const choices = [base, decoded, ...['.ts', '.tsx', '.js', '.jsx', '.mjs', '.py', '/index.ts', '/index.js'].map(x => base + x)];
        const target = choices.find(c => byPath.has(c));
        if (target) refs.get(target).push({ path: f.path, line: i + 1, kind: m[2] ? 'markdown-link' : 'literal-reference' });
        else if (m[2] && !spec.startsWith('/')) unresolved.push({ path: f.path, line: i + 1, target: spec, kind: 'unresolved-local-link', uncertainty: 'May be a route, generated artifact, or externally supplied file.' });
      }
    }
  }
  const candidates = new Map();
  function add(f, reason) {
    if (!candidates.has(f.path)) candidates.set(f.path, { path: f.path, sha256: f.sha256, bytes: f.bytes, test: f.test, protection: f.protection, references: refs.get(f.path), evidence: [], uncertainty: 'Review required. Static references omit dynamic loading, framework discovery, external consumers and hidden configuration.' });
    candidates.get(f.path).evidence.push(reason);
  }
  const groups = new Map();
  for (const f of files) {
    if (f.text === null || f.bytes === 0) continue;
    const group = groups.get(f.sha256) || []; group.push(f); groups.set(f.sha256, group);
  }
  for (const group of groups.values()) if (group.length > 1) for (const f of group) add(f, { kind: 'exact-duplicate', peers: group.filter(p => p !== f).map(p => p.path), note: 'Byte identity does not establish equivalent purpose or test coverage.' });
  const docs = files.filter(f => doc(f.path) && f.text !== null && f.text.length >= 160);
  const tokens = f => new Set(f.text.toLowerCase().match(/[\p{L}\p{N}_]+/gu) || []);
  const sets = new Map(docs.map(f => [f.path, tokens(f)]));
  // Bound quadratic work explicitly. Full inventory and exact duplicates remain complete.
  for (let a = 0; a < Math.min(docs.length, 300); a++) for (let b = a + 1; b < Math.min(docs.length, 300); b++) {
    const left = docs[a], right = docs[b];
    if (left.sha256 === right.sha256) continue;
    const x = sets.get(left.path), y = sets.get(right.path);
    const common = [...x].filter(t => y.has(t)).length;
    const ratio = common / (x.size + y.size - common);
    if (ratio >= 0.82) for (const [f, peer] of [[left, right], [right, left]]) add(f, { kind: 'near-duplicate-document', peer: peer.path, tokenJaccard: Number(ratio.toFixed(3)), note: 'Token overlap is a review lead; instructions, examples and numbers may differ.' });
  }
  for (const f of files) {
    if (f.text === null) continue;
    if ((doc(f.path) || source(f.path)) && !refs.get(f.path).length) add(f, { kind: 'no-observed-inbound-reference', note: 'Not proof of being unused; entrypoints and standalone documents are often valid.' });
    const marker = f.text.split('\n').findIndex(l => /(?:@generated|auto[- ]generated|do not edit)/i.test(l));
    if (marker >= 0) add(f, { kind: 'generated-marker', line: marker + 1, note: 'Identify generator and reproducible regeneration command before selection.' });
  }
  for (const link of unresolved) add(byPath.get(link.path), link);
  return { candidates: [...candidates.values()], limitations: ['No semantic dead-code or unused-export proof; inspect abstractions and runtime entrypoints manually.', 'No age-based staleness inference. Unresolved links require context.', 'Test count/size/duplication does not prove redundant verification.', 'Literal-reference scan is language-agnostic and incomplete; package scripts and path strings are evidence, not a full dependency graph.', ...(docs.length > 300 ? ['Near-document comparison limited to first 300 documents in inventory order.'] : [])] };
}
async function audit(root) {
  const scan = await inventory(root);
  const report = findings(scan.files);
  return { schemaVersion: 1, kind: 'compressor-audit', createdAt: new Date().toISOString(), root: await identity(root), gitAvailable: scan.gitAvailable, inventory: scan.files.map(({ text, ...f }) => f), skipped: scan.skipped, ...report };
}
function assertRecord(record, kind) {
  if (record.schemaVersion !== 1 || record.kind !== kind || !record.root) fail(`Expected ${kind} schemaVersion 1.`);
}
async function checkIdentity(root, expected) {
  if (json(await identity(root)) !== json(expected)) fail('Root identity changed; create a fresh audit.');
}
async function writeExclusive(file, value) { await fs.writeFile(file, json(value), { flag: 'wx', mode: 0o600 }); }
async function withLock(root, action) {
  const dir = await safe(root, STATE, true);
  await fs.mkdir(dir, { recursive: true, mode: 0o700 });
  await safe(root, STATE);
  const lock = await fs.open(path.join(dir, 'lock'), 'wx', 0o600).catch(e => fail(`State locked or unavailable: ${e.message}. After confirming no process is active, remove .pow/compressor/lock to recover.`));
  try { return await action(dir); } finally { await lock.close(); await fs.unlink(path.join(dir, 'lock')); }
}
async function apply(root, plan) {
  assertRecord(plan, 'compressor-plan');
  await checkIdentity(root, plan.root);
  if (!Array.isArray(plan.decisions) || !Array.isArray(plan.inventory)) fail('Invalid plan lists.');
  const selected = plan.decisions.filter(d => d.action === 'quarantine');
  if (!selected.length) fail('No quarantine decisions selected. Audit and plan are read-only by default.');
  if (new Set(selected.map(d => String(d.path).toLowerCase())).size !== selected.length) fail('Duplicate selected paths.');
  return withLock(root, async dir => {
    const fresh = await inventory(root);
    const old = new Map(plan.inventory.map(f => [f.path, f]));
    const now = new Map(fresh.files.map(f => [f.path, f]));
    if (old.size !== now.size || [...old].some(([p, f]) => now.get(p)?.sha256 !== f.sha256)) fail('Inventory changed since audit; create a fresh audit/plan.');
    if (json(plan.skipped) !== json(fresh.skipped)) fail('Skipped paths changed since audit.');
    for (const d of selected) {
      relative(d.path);
      if (excluded(d.path)) fail(`Protected state/VCS path: ${d.path}`);
      const f = now.get(d.path);
      if (!f || d.sha256 !== f.sha256) fail(`Candidate hash mismatch: ${d.path}`);
      if (typeof d.rationale !== 'string' || !d.rationale.trim()) fail(`Per-path rationale required: ${d.path}`);
      if (f.protection.length && d.allowProtected !== true) fail(`Explicit allowProtected required (${f.protection.join(', ')}): ${d.path}`);
      if (f.test) {
        const v = d.verification;
        if (!v || ![v.rationale, v.preservedCapability, v.command, v.observedResult].every(x => typeof x === 'string' && x.trim()) || !Array.isArray(v.survivingPaths) || !v.survivingPaths.length) fail(`Test decision requires verification rationale, preservedCapability, survivingPaths, command and observedResult: ${d.path}`);
        for (const p of v.survivingPaths) if (!now.has(p) || selected.some(s => s.path === p)) fail(`Verification survivor unavailable: ${p}`);
      }
      await safe(root, d.path);
    }
    const run = randomUUID(), runDir = path.join(dir, run);
    await fs.mkdir(runDir, { mode: 0o700 });
    const record = { schemaVersion: 1, kind: 'compressor-run', root: plan.root, run, createdAt: new Date().toISOString(), entries: selected.map((d, i) => ({ ...d, backup: `${i}.backup`, mode: now.get(d.path).mode, status: 'pending' })) };
    await writeExclusive(path.join(runDir, 'manifest.json'), record);
    // Back up every selected byte before removing any original. Journal survives interruptions.
    for (const entry of record.entries) {
      const src = await safe(root, entry.path);
      await fs.copyFile(src, path.join(runDir, entry.backup), constants.COPYFILE_EXCL);
      await fs.chmod(path.join(runDir, entry.backup), 0o600);
      if (hash(await fs.readFile(path.join(runDir, entry.backup))) !== entry.sha256) fail(`Backup mismatch: ${entry.path}; originals retained.`);
    }
    for (const entry of record.entries) {
      const src = await safe(root, entry.path);
      if (hash(await fs.readFile(src)) !== entry.sha256) fail(`Changed during apply: ${entry.path}; restore run ${run} for any earlier entries.`);
      await fs.unlink(src);
      entry.status = 'quarantined';
    }
    // Original manifest already contains complete recovery information; final status is separate.
    await writeExclusive(path.join(runDir, 'completed.json'), { completedAt: new Date().toISOString() });
    return { run, quarantined: record.entries.map(e => e.path), recovery: `restore --root ${JSON.stringify(root)} --run ${run}`, note: 'Backups retained. References were not rewritten; run project verification now.' };
  });
}
async function restore(root, run) {
  if (!/^[a-f0-9-]{36}$/.test(run || '')) fail('Invalid run ID.');
  return withLock(root, async () => {
    const runDir = await safe(root, `${STATE}/${run}`);
    const record = JSON.parse(await fs.readFile(await safe(root, `${STATE}/${run}/manifest.json`), 'utf8'));
    assertRecord(record, 'compressor-run');
    await checkIdentity(root, record.root);
    const restored = [], conflicts = [], unchanged = [];
    for (const entry of record.entries) {
      relative(entry.path);
      if (excluded(entry.path) || !/^\d+\.backup$/.test(entry.backup)) fail('Unsafe recovery entry.');
      const dest = await safe(root, entry.path, true);
      const existing = await fs.lstat(dest).catch(e => e.code === 'ENOENT' ? null : Promise.reject(e));
      if (existing) {
        if (existing.isFile() && hash(await fs.readFile(dest)) === entry.sha256) unchanged.push(entry.path);
        else conflicts.push(entry.path);
        continue;
      }
      const backup = await safe(root, `${STATE}/${run}/${entry.backup}`);
      if (hash(await fs.readFile(backup)) !== entry.sha256) fail(`Corrupt backup: ${entry.path}`);
      await fs.mkdir(path.dirname(dest), { recursive: true });
      await safe(root, entry.path, true);
      await fs.copyFile(backup, dest, constants.COPYFILE_EXCL);
      await fs.chmod(dest, entry.mode & 0o777);
      restored.push(entry.path);
    }
    return { run, restored, unchanged, conflicts, note: 'Backups retained; conflicts are never overwritten. Resolve/move new work and rerun restore.' };
  });
}
async function main() {
  if (Number(process.versions.node.split('.')[0]) < 20) fail('Node 20 or later required.');
  const [command = 'help', ...args] = process.argv.slice(2), opts = {};
  for (let i = 0; i < args.length; i += 2) {
    if (!['--root', '--audit', '--plan', '--run', '--out'].includes(args[i]) || !args[i + 1] || args[i + 1].startsWith('--') || opts[args[i]]) fail(`Invalid option: ${args[i]}`);
    opts[args[i]] = args[i + 1];
  }
  if (command === 'help' || command === '--help') {
    console.log('compressor (Node 20+)\n  audit --root DIR [--out NEW.json]\n  plan --root DIR --audit audit.json [--out NEW.json]\n  apply --root DIR --plan reviewed-plan.json\n  restore --root DIR --run UUID\nAudit/plan print JSON unless --out creates a new file. Edit individual plan decisions to action="quarantine" and supply rationale. State: .pow/compressor/. No permanent deletion command.');
    return;
  }
  if (!opts['--root']) fail('--root is required.');
  const requested = path.resolve(opts['--root']);
  const root = await fs.realpath(requested);
  if (requested.toLowerCase() !== root.toLowerCase() || (await fs.lstat(requested)).isSymbolicLink()) fail('Root must be a real directory, not a link/junction.');
  let result;
  if (command === 'audit') result = await audit(root);
  else if (command === 'plan') {
    if (!opts['--audit']) fail('--audit is required.');
    const report = JSON.parse(await fs.readFile(opts['--audit'], 'utf8'));
    assertRecord(report, 'compressor-audit');
    await checkIdentity(root, report.root);
    result = { schemaVersion: 1, kind: 'compressor-plan', root: report.root, createdAt: new Date().toISOString(), inventory: report.inventory, skipped: report.skipped, limitations: report.limitations, decisions: report.candidates.map(f => ({ ...f, action: 'retain', rationale: '', allowProtected: false, ...(f.test ? { verification: { rationale: '', preservedCapability: '', survivingPaths: [], command: '', observedResult: '' } } : {}) })) };
  } else if (command === 'apply') {
    if (!opts['--plan']) fail('--plan is required.');
    if (opts['--out']) fail('--out is only supported for audit/plan.');
    result = await apply(root, JSON.parse(await fs.readFile(opts['--plan'], 'utf8')));
  } else if (command === 'restore') {
    if (opts['--out']) fail('--out is only supported for audit/plan.');
    result = await restore(root, opts['--run']);
    if (result.conflicts.length) process.exitCode = 2;
  } else fail(`Unknown command: ${command}`);
  if (opts['--out']) {
    const requestedOut = path.resolve(opts['--out']);
    const out = path.join(await fs.realpath(path.dirname(requestedOut)), path.basename(requestedOut));
    if (inside(root, out)) fail('--out must be outside the audited root to avoid changing its inventory.');
    await writeExclusive(out, result);
    console.log(json({ written: out }));
  } else process.stdout.write(json(result));
}
main().catch(error => { console.error(`compressor: ${error.message}`); process.exitCode = 1; });
