import test from 'node:test';
import assert from 'node:assert/strict';
import { runTasks } from './tasks.mjs';

const tick = () => new Promise(setImmediate);
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('shares the total cap across tasks and preserves repeated local IDs', async () => {
  const gates = [deferred(), deferred(), deferred()]; const calls = []; let active = 0; let maximum = 0;
  const pending = runTasks(['a', 'b', 'c'].map(id => ({ id, jobs: [{ id: 'same' }] })), {
    concurrency: 2, invoke: async (job, context) => {
      const index = calls.length; calls.push([context.taskId, job.id, context.localId]);
      maximum = Math.max(maximum, ++active); await gates[index].promise; active--; return context.taskId;
    },
  });
  await tick(); assert.equal(calls.length, 2);
  gates[0].resolve(); await tick(); assert.equal(calls.length, 3);
  gates[1].resolve(); gates[2].resolve(); const result = await pending;
  assert.equal(maximum, 2); assert.deepEqual(result.tasks.map(task => task.jobs[0].value), ['a', 'b', 'c']);
  assert.deepEqual(calls, [['a', 'same', 'same'], ['b', 'same', 'same'], ['c', 'same', 'same']]);
});

test('resource keys serialize conflicting writes across tasks', async () => {
  const gate = deferred(); const calls = [];
  const pending = runTasks([{ id: 'a', jobs: [{ id: 'write', writes: ['shared'] }] },
    { id: 'b', jobs: [{ id: 'read', reads: ['shared'] }] }], {
    concurrency: 8, invoke: async (job, { taskId }) => { calls.push(taskId); if (taskId === 'a') await gate.promise; },
  });
  await tick(); assert.deepEqual(calls, ['a']); gate.resolve(); await pending; assert.deepEqual(calls, ['a', 'b']);
});

test('isolates failures and decodes dependency and observer metadata', async () => {
  const observed = []; const calls = [];
  const result = await runTasks([{ id: 'bad:0', jobs: [{ id: 'root' }, { id: 'tail', depends_on: ['root'] }] },
    { id: 'good', jobs: [{ id: 'root' }, { id: 'tail', depends_on: ['root'] }] }], {
    invoke: (job, { taskId }) => { calls.push(`${taskId}/${job.id}`); if (taskId === 'bad:0') throw new Error('failure'); },
    onEvent: event => { observed.push(event); if (event.type === 'failed') throw new Error('observer failure'); },
  });
  assert.deepEqual(result.tasks.map(task => task.status), ['failed', 'completed']);
  assert.deepEqual(result.tasks[0].jobs[1].blocked_by, ['root']);
  assert.equal(calls.includes('bad:0/tail'), false); assert.equal(calls.includes('good/tail'), true);
  assert.equal(observed.every(event => ['bad:0', 'good'].includes(event.taskId)), true);
  assert.equal(result.observer_errors[0].taskId, 'bad:0'); assert.equal(result.observer_errors[0].id, 'root');
});

test('critical path priority is global across task graphs', async () => {
  const calls = [];
  await runTasks([{ id: 'short', jobs: [{ id: 'one', estimated_s: 2 }] },
    { id: 'long', jobs: [{ id: 'root' }, { id: 'tail', depends_on: ['root'], estimated_s: 9 }] }], {
    concurrency: 1, invoke: (job, { taskId }) => calls.push(`${taskId}/${job.id}`),
  });
  assert.deepEqual(calls, ['long/root', 'long/tail', 'short/one']);
});

test('validates every task and graph before any invocation', async () => {
  const good = { id: 'good', jobs: [{ id: 'one' }] }; let calls = 0;
  for (const tasks of [null, [good, good], [good, { id: 'empty', jobs: [] }],
    [good, { id: 'bad', jobs: [{ id: 'x' }, { id: 'x' }] }],
    [good, { id: 'bad', jobs: [{ id: 'x', depends_on: ['one'] }] }],
    [good, { id: 'bad', jobs: [{ id: 'x', estimated_s: 0 }] }],
    [good, { id: 'bad', depends_on: [], jobs: [{ id: 'x' }] }],
    [good, { id: 'bad', jobs: [{ id: 'x', depends_on: ['x'] }] }]]) {
    await assert.rejects(runTasks(tasks, { invoke: () => calls++ }), TypeError);
  }
  assert.equal(calls, 0);
  assert.deepEqual((await runTasks([], { invoke: () => calls++ })).tasks, []);
});

test('cancellation is shared and marks every unstarted task blocked', async () => {
  const controller = new AbortController(); controller.abort(); let calls = 0;
  const result = await runTasks(['a', 'b'].map(id => ({ id, jobs: [{ id: 'one' }] })), {
    signal: controller.signal, invoke: () => calls++,
  });
  assert.equal(calls, 0); assert.deepEqual(result.tasks.map(task => task.status), ['blocked', 'blocked']);
});
