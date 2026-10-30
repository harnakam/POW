#!/usr/bin/env node
import { readFile, writeFile, open, rename, unlink, lstat } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID, createHash } from 'node:crypto';

const usage = 'tasks.mjs init <ledger> <plan.json> | add <ledger> <tasks.json> | start <ledger> <id> <workspace> <session> | finish <ledger> <id> <evidence.json> | block <ledger> <id> <reason> | retry <ledger> <id> | status <ledger>';
const text = value => typeof value === 'string' && value.trim().length > 0;
const readJson = async file => JSON.parse(await readFile(file, 'utf8'));
const fail = message => { throw new Error(message); };

function ownedPath(value) {
  if (!text(value)) fail('Owned paths must be nonempty strings');
  const normalized = value.replaceAll('\\', '/');
  if (normalized.startsWith('/') || normalized.split('/').some(p => !p || p === '.' || p === '..' || /[:*?"<>|]|[. ]$/.test(p))) {
    fail(`Use literal repository-relative paths, without traversal or globs: ${value}`);
  }
  return normalized.toLowerCase();
}

const overlaps = (a, b) => a === b || a.startsWith(`${b}/`) || b.startsWith(`${a}/`);

function checkEvidence(evidence) {
  if (!evidence || !text(evidence.integration) || !Array.isArray(evidence.checks) || !evidence.checks.length ||
      evidence.checks.some(check => !check || !text(check.command) || check.exitCode !== 0 || !text(check.artifact))) {
    fail('Evidence requires integration notes and checks with command, exitCode: 0, and artifact');
  }
}

function validate(ledger) {
  if (!ledger || ledger.version !== 1 || !text(ledger.goal) || !text(ledger.baseline) || !Array.isArray(ledger.tasks)) fail('Invalid ledger schema');
  const tasks = new Map();
  for (const task of ledger.tasks) {
    if (!task || !text(task.id) || !/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(task.id) || tasks.has(task.id)) fail('Invalid or duplicate task ID');
    if (!text(task.objective) || !Array.isArray(task.dependsOn) || task.dependsOn.some(id => !text(id)) || new Set(task.dependsOn).size !== task.dependsOn.length ||
        !Array.isArray(task.owns) || !task.owns.length || !Array.isArray(task.acceptance) || !task.acceptance.length || task.acceptance.some(item => !text(item))) fail(`Invalid task contract: ${task.id}`);
    const owns = task.owns.map(ownedPath);
    if (new Set(owns).size !== owns.length) fail(`Duplicate owned path: ${task.id}`);
    if (!['pending', 'running', 'done', 'blocked'].includes(task.status)) fail(`Invalid status: ${task.id}`);
    if (task.status === 'running' && (!text(task.workspace) || !text(task.session))) fail(`Missing worker identity: ${task.id}`);
    if (task.status === 'blocked' && !text(task.reason)) fail(`Missing block reason: ${task.id}`);
    if (task.status === 'done') {
      checkEvidence(task.evidence);
      if (task.evidence.checks.some(check => !/^[a-f0-9]{64}$/.test(check.sha256) || !Number.isSafeInteger(check.bytes) || check.bytes < 1)) fail(`Missing artifact fingerprint: ${task.id}`);
    }
    tasks.set(task.id, task);
  }
  const visited = new Set();
  const active = new Set();
  function visit(id) {
    if (active.has(id)) fail(`Dependency cycle: ${id}`);
    if (visited.has(id)) return;
    const task = tasks.get(id);
    if (!task) fail(`Unknown dependency: ${id}`);
    active.add(id);
    task.dependsOn.forEach(visit);
    active.delete(id);
    visited.add(id);
  }
  tasks.forEach(task => {
    visit(task.id);
    if (['running', 'done'].includes(task.status) && task.dependsOn.some(id => tasks.get(id).status !== 'done')) fail(`Unfinished dependency: ${task.id}`);
  });
  const running = ledger.tasks.filter(task => task.status === 'running');
  for (let i = 0; i < running.length; i++) {
    for (const other of running.slice(i + 1)) {
      if (running[i].owns.some(a => other.owns.some(b => overlaps(ownedPath(a), ownedPath(b))))) fail(`Ownership conflict: ${running[i].id} / ${other.id}`);
    }
  }
}

function newTasks(tasks) {
  if (!Array.isArray(tasks)) fail('Expected a tasks array');
  return tasks.map(task => {
    if (!task || Object.keys(task).some(key => !['id', 'objective', 'dependsOn', 'owns', 'acceptance'].includes(key))) fail('Task input allows id, objective, dependsOn, owns, acceptance only');
    return { ...task, status: 'pending' };
  });
}

function summary(ledger) {
  const done = new Set(ledger.tasks.filter(task => task.status === 'done').map(task => task.id));
  const running = ledger.tasks.filter(task => task.status === 'running');
  return { ...ledger, ready: ledger.tasks.filter(task => task.status === 'pending' && task.dependsOn.every(id => done.has(id)) &&
    !running.some(other => task.owns.some(a => other.owns.some(b => overlaps(ownedPath(a), ownedPath(b)))))).map(task => task.id) };
}

async function main() {
  const [command, ledgerArg, ...args] = process.argv.slice(2);
  const arity = { init: 1, add: 1, start: 3, finish: 2, block: 2, retry: 1, status: 0 };
  if (!Object.hasOwn(arity, command) || !ledgerArg || args.length !== arity[command]) fail(usage);
  const file = path.resolve(ledgerArg);
  if (command === 'status') {
    const ledger = await readJson(file);
    validate(ledger);
    console.log(JSON.stringify(summary(ledger), null, 2));
    return;
  }
  const lockFile = `${file}.lock`;
  let lock;
  try { lock = await open(lockFile, 'wx', 0o600); }
  catch (error) {
    if (error.code === 'EEXIST') fail(`Ledger locked: ${lockFile}. Check the owner process before recovering a stale lock.`);
    throw error;
  }
  const temporary = `${file}.${randomUUID()}.tmp`;
  try {
    await lock.writeFile(JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }));
    let ledger;
    if (command === 'init') {
      try { await lstat(file); fail('Ledger already exists'); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
      const plan = await readJson(args[0]);
      ledger = { version: 1, goal: plan.goal, baseline: plan.baseline, tasks: newTasks(plan.tasks) };
    } else {
      if ((await lstat(file)).isSymbolicLink()) fail('Ledger must not be a symbolic link');
      ledger = await readJson(file);
      validate(ledger);
      if (command === 'add') ledger.tasks.push(...newTasks(await readJson(args[0])));
      else {
        const task = ledger.tasks.find(item => item.id === args[0]);
        if (!task) fail(`Unknown task: ${args[0]}`);
        if (command === 'start') {
          if (task.status !== 'pending') fail('Only pending tasks can start');
          if (!path.isAbsolute(args[1]) || !text(args[2])) fail('Start requires an absolute workspace and a process/session identity');
          Object.assign(task, { status: 'running', workspace: args[1], session: args[2] });
        } else if (command === 'finish') {
          if (task.status !== 'running') fail('Only running tasks can finish');
          const evidence = await readJson(args[1]);
          checkEvidence(evidence);
          for (const check of evidence.checks) {
            const artifact = path.resolve(path.dirname(file), check.artifact);
            const contents = await readFile(artifact);
            if (!contents.length) fail(`Empty evidence artifact: ${artifact}`);
            Object.assign(check, { artifact, bytes: contents.length, sha256: createHash('sha256').update(contents).digest('hex') });
          }
          Object.assign(task, { status: 'done', evidence });
        } else if (command === 'block') {
          if (!['pending', 'running'].includes(task.status) || !text(args[1])) fail('Block requires a pending/running task and reason');
          Object.assign(task, { status: 'blocked', reason: args[1] });
        } else if (command === 'retry') {
          if (task.status !== 'blocked') fail('Only blocked tasks can retry');
          task.status = 'pending';
          delete task.reason;
          delete task.workspace;
          delete task.session;
        }
      }
    }
    validate(ledger);
    ledger.updatedAt = new Date().toISOString();
    await writeFile(temporary, `${JSON.stringify(ledger, null, 2)}\n`, { flag: 'wx', mode: 0o600 });
    await rename(temporary, file);
    console.log(JSON.stringify(summary(ledger), null, 2));
  } finally {
    await unlink(temporary).catch(error => { if (error.code !== 'ENOENT') throw error; });
    await lock.close();
    await unlink(lockFile);
  }
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
