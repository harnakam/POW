#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { StringDecoder } from 'node:string_decoder';

const hash = (value) => createHash('sha256').update(value).digest('hex');
const nonempty = (value) => typeof value === 'string' && value.trim().length > 0;
const fail = (message) => { throw new Error(message); };
const integer = (value, min, max) => Number.isSafeInteger(value) && value >= min && value <= max;

export function validateSuite(suite) {
  if (suite?.version !== 1) fail('Suite version must be 1.');
  if (!nonempty(suite.name) || !nonempty(suite.environment)) fail('Name and environment are required.');
  if (!nonempty(suite.evaluator)) fail('A self-contained Node evaluator path is required.');
  if (!integer(suite.repetitions, 1, 20)) fail('Repetitions must be 1..20.');
  if (!integer(suite.timeoutMs, 50, 3600000)) fail('timeoutMs must be 50..3600000.');
  if (!integer(suite.maxCalls, 2, 1000)) fail('maxCalls must be 2..1000.');
  for (const name of ['baseline', 'candidate']) {
    if (!nonempty(suite[name])) fail(`${name} artifact path is required.`);
  }
  if (!Array.isArray(suite.cases) || suite.cases.length === 0) fail('Cases cannot be empty.');
  const ids = new Set();
  const inputs = new Set();
  for (const item of suite.cases) {
    if (!nonempty(item.id) || ids.has(item.id)) fail('Case IDs must be nonempty and unique.');
    ids.add(item.id);
    if (!['development', 'holdout'].includes(item.split)) fail('Case split must be development or holdout.');
    if (!Object.hasOwn(item, 'input')) fail(`Case ${item.id} has no input.`);
    const key = JSON.stringify(canonical(item.input));
    if (inputs.has(key)) fail('Duplicate case inputs would bias the comparison or leak across splits.');
    inputs.add(key);
    if (!Array.isArray(item.checks) || !item.checks.length || item.checks.some((id) => !nonempty(id)) || new Set(item.checks).size !== item.checks.length) {
      fail(`Case ${item.id} needs unique, nonempty check IDs.`);
    }
  }
  if (!suite.cases.some((item) => item.split === 'holdout')) fail('At least one holdout case is required.');
  if (!suite.cases.some((item) => item.split === 'development')) fail('At least one development case is required.');
  const calls = suite.cases.length * suite.repetitions * 2;
  if (calls > suite.maxCalls) fail(`Planned ${calls} calls exceed maxCalls ${suite.maxCalls}.`);
  return calls;
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  return value;
}

function validateResult(value, checks) {
  if (!value || !Array.isArray(value.checks) || value.checks.length !== checks.length) fail('Evaluator must return every declared check exactly once.');
  const ids = new Set();
  for (const check of value.checks) {
    if (!checks.includes(check.id) || ids.has(check.id) || typeof check.passed !== 'boolean' || !nonempty(check.evidence)) {
      fail('Invalid check ID, boolean verdict, or evidence.');
    }
    ids.add(check.id);
  }
  if (value.tokens != null && !integer(value.tokens, 0, Number.MAX_SAFE_INTEGER)) fail('tokens must be a nonnegative integer when known.');
  return { checks: value.checks, tokens: value.tokens ?? null };
}

function execute(evaluator, input, cwd, timeoutMs) {
  return new Promise((resolve) => {
    const started = performance.now();
    let stdout = '', stderr = '', bytes = 0, error = null;
    const outDecoder = new StringDecoder('utf8');
    const errDecoder = new StringDecoder('utf8');
    let completed = false, cleanupTimer;
    const child = spawn(process.execPath, [evaluator], {
      cwd, shell: false, windowsHide: true, detached: process.platform !== 'win32',
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    const stop = (reason) => {
      if (error) return;
      error = reason;
      cleanupTimer = setTimeout(() => {
        error += '; process cleanup unconfirmed; inspect worker PID ' + child.pid;
        child.stdout.destroy(); child.stderr.destroy(); child.stdin.destroy();
        child.unref();
        finish(null, null);
      }, 2000);
      if (!child.pid) return;
      if (process.platform === 'win32') {
        const killer = spawn('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
        killer.on('error', () => child.kill());
        killer.on('close', (code) => { if (code !== 0) child.kill(); });
      } else {
        try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); }
      }
    };
    const timer = setTimeout(() => stop('timeout'), timeoutMs);
    const interrupt = () => stop('interrupted');
    process.once('SIGINT', interrupt);
    process.once('SIGTERM', interrupt);
    function finish(code, signal) {
      if (completed) return;
      completed = true;
      clearTimeout(timer); clearTimeout(cleanupTimer);
      process.removeListener('SIGINT', interrupt); process.removeListener('SIGTERM', interrupt);
      stdout += outDecoder.end(); stderr += errDecoder.end();
      resolve({ stdout, stderr, exitCode: code, signal, error, durationMs: performance.now() - started });
    }
    child.on('error', (err) => { error = `spawn: ${err.message}`; });
    child.stdin.on('error', () => {});
    child.stdout.on('data', (chunk) => {
      bytes += chunk.length;
      if (bytes > 1048576) stop('output_limit');
      else stdout += outDecoder.write(chunk);
    });
    child.stderr.on('data', (chunk) => {
      bytes += chunk.length;
      if (bytes > 1048576) stop('output_limit');
      else stderr += errDecoder.write(chunk);
    });
    child.on('close', finish);
    child.stdin.end(JSON.stringify(input));
  });
}

export function summarize(suite, records) {
  const splits = {};
  for (const split of ['development', 'holdout']) {
    const pairs = [];
    for (const item of suite.cases.filter((entry) => entry.split === split)) {
      for (let repeat = 0; repeat < suite.repetitions; repeat++) {
        const select = (variant) => records.filter((row) => row.caseId === item.id && row.repeat === repeat && row.variant === variant);
        const baseline = select('baseline');
        const candidate = select('candidate');
        if (baseline.length !== 1 || candidate.length !== 1 || baseline[0].status !== 'ok' || candidate[0].status !== 'ok') {
          pairs.push({ caseId: item.id, repeat, status: 'invalid' });
          continue;
        }
        // Revalidate imported records rather than trusting a success label.
        try {
          validateResult(baseline[0], item.checks);
          validateResult(candidate[0], item.checks);
        } catch {
          pairs.push({ caseId: item.id, repeat, status: 'invalid' });
          continue;
        }
        for (const id of item.checks) {
          const before = baseline[0].checks.find((check) => check.id === id).passed;
          const after = candidate[0].checks.find((check) => check.id === id).passed;
          pairs.push({ caseId: item.id, repeat, check: id, status: before === after ? 'same' : after ? 'improved' : 'regressed' });
        }
      }
    }
    const count = (status) => pairs.filter((pair) => pair.status === status).length;
    splits[split] = { improved: count('improved'), regressed: count('regressed'), invalid: count('invalid'), same: count('same'), pairs };
  }
  const invalid = Object.values(splits).some((split) => split.invalid > 0);
  const regressed = Object.values(splits).some((split) => split.regressed > 0);
  const verdict = invalid ? 'inconclusive' : regressed ? 'regression' : splits.holdout.improved > 0 ? 'candidate-better-on-suite' : 'no-demonstrated-improvement';
  const variants = Object.fromEntries(['baseline', 'candidate'].map((variant) => {
    const rows = records.filter((row) => row.variant === variant);
    const valid = rows.filter((row) => row.status === 'ok');
    return [variant, {
      completed: valid.length, attempted: rows.length,
      processDurationMs: rows.reduce((sum, row) => sum + row.durationMs, 0),
      tokens: rows.length && rows.every((row) => Number.isSafeInteger(row.tokens)) ? rows.reduce((sum, row) => sum + row.tokens, 0) : null,
    }];
  }));
  return { verdict, splits, variants, interpretation: 'Paired outcomes on this frozen suite; not a statistical significance or general superiority claim. Process duration includes evaluator startup and checks.' };
}

export async function runSuite(suiteFile, outputDirectory) {
  const suitePath = path.resolve(suiteFile);
  const suiteBytes = await readFile(suitePath);
  const suite = JSON.parse(suiteBytes.toString('utf8'));
  const calls = validateSuite(suite);
  const root = path.dirname(suitePath);
  const artifacts = {};
  for (const key of ['evaluator', 'baseline', 'candidate']) {
    const source = path.resolve(root, suite[key]);
    artifacts[key] = { source, bytes: await readFile(source), extension: path.extname(source) };
  }
  if (artifacts.evaluator.extension !== '.mjs') fail('Evaluator must be a self-contained .mjs file.');
  const output = path.resolve(outputDirectory);
  // Exclusive directory creation prevents concurrent writers and accidental overwrite.
  await mkdir(output);
  await mkdir(path.join(output, 'snapshots'));
  for (const [key, artifact] of Object.entries(artifacts)) {
    artifact.snapshot = path.join(output, 'snapshots', `${key}${artifact.extension}`);
    await writeFile(artifact.snapshot, artifact.bytes, { flag: 'wx' });
  }
  const manifest = {
    version: 1, name: suite.name, startedAt: new Date().toISOString(), calls,
    suiteSha256: hash(suiteBytes), node: process.version, platform: process.platform,
    declaredEnvironment: suite.environment,
    artifacts: Object.fromEntries(Object.entries(artifacts).map(([key, artifact]) => [key, { source: artifact.source, sha256: hash(artifact.bytes) }])),
  };
  await writeFile(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2));
  await writeFile(path.join(output, 'suite.json'), suiteBytes);
  const records = [];
  for (const item of suite.cases) {
    for (let repeat = 0; repeat < suite.repetitions; repeat++) {
      const order = (suite.cases.indexOf(item) + repeat) % 2 ? ['candidate', 'baseline'] : ['baseline', 'candidate'];
      for (const variant of order) {
        const runDirectory = path.join(output, `run-${String(records.length + 1).padStart(4, '0')}`);
        await mkdir(runDirectory);
        const result = await execute(artifacts.evaluator.snapshot, {
          version: 1, artifact: artifacts[variant].snapshot, input: item.input,
        }, runDirectory, suite.timeoutMs);
        const record = { caseId: item.id, split: item.split, repeat, variant, durationMs: result.durationMs, exitCode: result.exitCode, status: 'error', tokens: null };
        try {
          if (result.error) fail(result.error);
          if (result.exitCode !== 0) fail(`Evaluator exited ${result.exitCode}, signal ${result.signal}.`);
          Object.assign(record, validateResult(JSON.parse(result.stdout), item.checks), { status: 'ok' });
        } catch (error) { record.error = error.message; }
        // Mutating a supposedly frozen artifact invalidates the run.
        for (const [key, artifact] of Object.entries(artifacts)) {
          try {
            if (hash(await readFile(artifact.snapshot)) !== hash(artifact.bytes)) fail(`${key} snapshot changed`);
          } catch (error) { record.status = 'error'; record.error = error.message; }
        }
        await writeFile(path.join(runDirectory, 'stdout.txt'), result.stdout);
        await writeFile(path.join(runDirectory, 'stderr.txt'), result.stderr);
        await writeFile(path.join(runDirectory, 'result.json'), JSON.stringify(record, null, 2));
        records.push(record);
        if (record.status !== 'ok') {
          const report = { ...manifest, ...summarize(suite, records), records };
          await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
          return report;
        }
      }
    }
  }
  const report = { ...manifest, ...summarize(suite, records), records };
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  return report;
}

export async function main(args) {
  if (args.length !== 3 || args[0] !== 'run') {
    console.error('Usage: node prove.mjs run <suite.json> <new-output-directory>');
    return 1;
  }
  try {
    const report = await runSuite(args[1], args[2]);
    console.log(JSON.stringify({ verdict: report.verdict, report: path.resolve(args[2], 'report.json') }));
    return report.verdict === 'inconclusive' || report.verdict === 'regression' ? 2 : 0;
  } catch (error) { console.error(error.message); return 1; }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = await main(process.argv.slice(2));
