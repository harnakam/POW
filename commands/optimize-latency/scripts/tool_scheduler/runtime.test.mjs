import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

test('fixed-source bundle exports both schedulers and executes two task graphs', async () => {
  const artifact = JSON.parse(await readFile(new URL('./runtime-bundle.json', import.meta.url), 'utf8'));
  const source = await readFile(new URL('./runtime.bundle.js', import.meta.url), 'utf8');
  assert.equal(artifact.source, source);
  assert.equal(createHash('sha256').update(source).digest('hex'), artifact.sha256);
  // Only the generated, reviewed local source is evaluated. The hash audits
  // artifact consistency; it is not an authorization or trust mechanism.
  const { runJobs, runTasks, runToolTasks } = Function(source)();
  assert.equal(typeof runJobs, 'function'); assert.equal(typeof runTasks, 'function');
  const result = await runTasks([
    { id: 'first', jobs: [{ id: 'read' }, { id: 'finish', depends_on: ['read'] }] },
    { id: 'second', jobs: [{ id: 'read' }] },
  ], { concurrency: 2, invoke: (job, { taskId }) => `${taskId}/${job.id}` });
  assert.deepEqual(result.tasks.map(task => task.status), ['completed', 'completed']);
  assert.deepEqual(result.tasks.map(task => task.jobs.at(-1).value), ['first/finish', 'second/read']);
  const routed = await runToolTasks([{ id: 'routed', run: t => t.echo('ok') }], { tools: { echo: value => value } });
  assert.equal(routed.tasks[0].value, 'ok');
});
