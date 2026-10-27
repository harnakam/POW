import test from 'node:test';
import assert from 'node:assert/strict';
import { runToolTasks } from './router.mjs';

const tick = () => new Promise(setImmediate);
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('intercepts automatic calls with global and per-task concurrency caps', async () => {
  const gates = Array.from({ length: 4 }, deferred); const started = []; let active = 0; let maximum = 0;
  const tools = { async native(value) { assert.equal(this, tools); started.push(value); maximum = Math.max(maximum, ++active); await gates[value].promise; active--; return { value }; } };
  const pending = runToolTasks([
    { id: 'a', run: async t => Promise.all([t.native(0), t.native(1)]) },
    { id: 'b', run: async t => Promise.all([t.native(2), t.native(3)]) },
  ], { tools, toolConcurrency: 2 });
  await tick(); assert.deepEqual(started, [0, 2]);
  gates[0].resolve(); await tick(); assert.deepEqual(started, [0, 2, 1]);
  gates[2].resolve(); await tick(); assert.deepEqual(started, [0, 2, 1, 3]);
  gates[1].resolve(); gates[3].resolve(); const result = await pending;
  assert.equal(maximum, 2); assert.deepEqual(result.tasks[0].value, [{ value: 0 }, { value: 1 }]);
  assert.equal(result.tool_events.length, 8);
  assert.equal(result.tool_events.some(event => 'args' in event || 'value' in event), false);
});

test('holds whole-task write leases until forgotten calls drain even after callback failure', async () => {
  const gate = deferred(); const started = [];
  const pending = runToolTasks([
    { id: 'a', writes: ['shared'], run: t => { t.wait(); throw new Error('callback'); } },
    { id: 'b', reads: ['shared'], run: () => started.push('b') },
    { id: 'independent', run: () => started.push('independent') },
  ], { tools: { wait: () => gate.promise } });
  await tick(); assert.deepEqual(started, ['independent']);
  gate.resolve(); const result = await pending;
  assert.deepEqual(started, ['independent', 'b']);
  assert.deepEqual(result.tasks.map(task => task.status), ['failed', 'completed', 'completed']);
});

test('preserves native errors, drains unawaited failures, and isolates observers', async () => {
  const nativeError = new Error('native failure'); let received; const order = [];
  const result = await runToolTasks([
    { id: 'a', run: async t => { try { await t.fail(); } catch (error) { received = error; } t.ok(); } },
    { id: 'b', run: t => t.ok() },
  ], { tools: { fail: () => { throw nativeError; }, ok: () => order.push('ok') },
    toolConcurrency: 1, onEvent: () => { throw new Error('observer'); } });
  assert.equal(received, nativeError); assert.equal(order.length, 2);
  assert.deepEqual(result.tasks.map(task => task.status), ['failed', 'completed']);
  assert.equal(result.tool_observer_errors.length, 6);
});

test('keeps native session return values unchanged and rejects invalid tasks before invocation', async () => {
  const session = { session_id: 123, output: 'partial' }; let calls = 0;
  const tools = { command: () => { calls++; return session; } };
  await assert.rejects(runToolTasks([{ id: 'a', run: t => t.command() }, { id: 'b' }], { tools }));
  assert.equal(calls, 0);
  const result = await runToolTasks([{ id: 'a', run: t => t.command() }], { tools });
  assert.equal(result.tasks[0].value, session);
});
