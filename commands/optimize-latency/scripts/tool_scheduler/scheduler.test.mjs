import test from 'node:test';
import assert from 'node:assert/strict';
import { runJobs } from './scheduler.mjs';

const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const tick = () => new Promise(setImmediate);

test('bounds concurrency, overlaps readers, and excludes writers', async () => {
  const gates = new Map(['a', 'b', 'c', 'd'].map(id => [id, deferred()]));
  const started = [];
  const pending = runJobs([
    { id: 'a', reads: ['db'] }, { id: 'b', reads: ['db'] },
    { id: 'c', writes: ['db'] }, { id: 'd' },
  ], { concurrency: 2, policy: 'fifo', invoke: async job => { started.push(job.id); await gates.get(job.id).promise; return job.id; } });
  await tick();
  assert.deepEqual(started, ['a', 'b']);
  gates.get('a').resolve(); await tick();
  assert.deepEqual(started, ['a', 'b', 'd']);
  gates.get('b').resolve(); await tick();
  assert.deepEqual(started, ['a', 'b', 'd', 'c']);
  gates.get('c').resolve(); gates.get('d').resolve();
  const result = await pending;
  assert.equal(result.jobs.every(j => j.status === 'completed' && j.duration_ms >= 0), true);
  assert.equal(result.events.filter(e => e.type === 'start').length, 4);
});

test('critical path prioritizes downstream work with stable input-order ties', async () => {
  const jobs = [{ id: 'short', estimated_s: 2 }, { id: 'root', estimated_s: 1 }, { id: 'tail', depends_on: ['root'], estimated_s: 9 }];
  for (const [policy, expected] of [['fifo', ['short', 'root', 'tail']], ['critical-path', ['root', 'tail', 'short']]]) {
    const started = [];
    await runJobs(jobs, { concurrency: 1, policy, invoke: async j => started.push(j.id) });
    assert.deepEqual(started, expected);
  }
  const order = [];
  await runJobs([{ id: 'a' }, { id: 'b' }], { concurrency: 1, invoke: j => order.push(j.id) });
  assert.deepEqual(order, ['a', 'b']);
});

test('failures block descendants while independent running work is awaited', async () => {
  const gate = deferred(); const calls = [];
  const pending = runJobs([{ id: 'bad' }, { id: 'child', depends_on: ['bad'] }, { id: 'grandchild', depends_on: ['child'] }, { id: 'good' }], {
    concurrency: 2, invoke: async j => { calls.push(j.id); if (j.id === 'bad') throw new Error('broken'); await gate.promise; },
  });
  let settled = false; pending.then(() => { settled = true; });
  await tick(); assert.equal(settled, false); gate.resolve();
  const result = await pending;
  assert.deepEqual(calls, ['bad', 'good']);
  assert.deepEqual(result.jobs.map(j => j.status), ['failed', 'blocked', 'blocked', 'completed']);
  assert.equal(result.events.filter(e => e.type === 'failed').length, 1);
});

test('dependencies must complete successfully before invocation', async () => {
  const gate = deferred(); const calls = [];
  const pending = runJobs([{ id: 'parent' }, { id: 'child', depends_on: ['parent'] }], {
    invoke: async j => { calls.push(j.id); if (j.id === 'parent') await gate.promise; },
  });
  await tick(); assert.deepEqual(calls, ['parent']); gate.resolve(); await pending;
  assert.deepEqual(calls, ['parent', 'child']);
});

test('rejects invalid graphs and claims before invoking anything', async () => {
  const invalid = [
    [{ id: 'a' }, { id: 'a' }], [{ id: 'a', depends_on: ['missing'] }],
    [{ id: 'a', depends_on: ['b'] }, { id: 'b', depends_on: ['a'] }],
    [{ id: 'a', estimated_s: Infinity }], [{ id: 'a', estimated_s: -1 }], [{ id: 'a', estimated_s: 0 }],
    [{ id: 'a', reads: [''] }], [{ id: 'a', writes: 'db' }],
    [{ id: 'a', depends_on: ['a'] }], [{ id: 'a', reads: ['db', 'db'] }],
  ];
  let calls = 0;
  for (const jobs of invalid) await assert.rejects(runJobs(jobs, { invoke: () => { calls++; } }));
  await assert.rejects(runJobs([], { concurrency: 0, invoke() {} }));
  await assert.rejects(runJobs([], { policy: 'unknown', invoke() {} }));
  await assert.rejects(runJobs([{ id: 'a' }], { onEvent: 'invalid', invoke: () => { calls++; } }));
  assert.equal(calls, 0);
});

test('live observer sees completion before dependent invocation and errors do not prevent draining', async () => {
  const gate = deferred(); const observed = []; let childSawCompletion = false;
  const pending = runJobs([{ id: 'parent' }, { id: 'child', depends_on: ['parent'] }, { id: 'independent' }], {
    concurrency: 2,
    onEvent: event => {
      observed.push(`${event.type}:${event.id}`);
      if (event.type === 'completed') throw new Error(`observer ${event.id}`);
    },
    invoke: async job => {
      if (job.id === 'independent') await gate.promise;
      if (job.id === 'child') childSawCompletion = observed.includes('completed:parent');
    },
  });
  let settled = false; pending.then(() => { settled = true; });
  await tick(); assert.equal(childSawCompletion, true); assert.equal(settled, false);
  gate.resolve(); const result = await pending;
  assert.equal(result.jobs.every(j => j.status === 'completed'), true);
  assert.equal(result.observer_errors.length, 3);
  assert.equal(result.observer_errors[0].error.message, 'observer parent');
});

test('async observer rejection is explicitly reported and observed', async () => {
  const result = await runJobs([{ id: 'a' }], { invoke: () => 1,
    onEvent: async event => { if (event.type === 'completed') throw new Error('async observer'); },
  });
  assert.equal(result.observer_errors.some(e => e.error.message === 'async observer'), true);
});

test('cancellation prevents pending starts and waits for cooperative running promises', async () => {
  const controller = new AbortController(); const gate = deferred(); const calls = [];
  const pending = runJobs([{ id: 'a' }, { id: 'b' }], {
    concurrency: 1, signal: controller.signal, invoke: async (j, { signal }) => {
      assert.equal(signal, controller.signal); calls.push(j.id); await gate.promise;
    },
  });
  await tick(); controller.abort(); let settled = false; pending.then(() => { settled = true; });
  await tick(); assert.equal(settled, false); gate.resolve();
  const result = await pending;
  assert.deepEqual(calls, ['a']); assert.equal(result.jobs[1].reason, 'cancelled');
  assert.equal(result.jobs[0].status, 'completed');
  const preCancelled = await runJobs([{ id: 'x' }], { signal: controller.signal, invoke: () => assert.fail('must not invoke') });
  assert.equal(preCancelled.jobs[0].status, 'blocked');
});

test('writers serialize only exact shared keys and synchronous throws become outcomes', async () => {
  const gate = deferred(); const calls = [];
  const pending = runJobs([
    { id: 'writer', writes: ['repo'] }, { id: 'same', writes: ['repo'] },
    { id: 'distinct', writes: ['repo/child'] },
  ], { concurrency: 3, policy: 'fifo', invoke: j => {
    calls.push(j.id);
    if (j.id === 'writer') return gate.promise;
    if (j.id === 'distinct') throw new Error('sync failure');
  } });
  await tick(); assert.deepEqual(calls, ['writer', 'distinct']);
  gate.resolve();
  const result = await pending;
  assert.deepEqual(calls, ['writer', 'distinct', 'same']);
  assert.equal(result.jobs[2].error.message, 'sync failure');
});
