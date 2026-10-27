import { setTimeout as delay } from 'node:timers/promises';
import { writeFile } from 'node:fs/promises';
import { runJobs } from './scheduler.mjs';

// FIFO fills both slots with independent work; priority opens the long chain early.
const jobs = [
  { id: 'independent-a', estimated_s: 0.06 },
  { id: 'independent-b', estimated_s: 0.06 },
  { id: 'chain-root', estimated_s: 0.01 },
  { id: 'chain-tail', depends_on: ['chain-root'], estimated_s: 0.12 },
];
const runs = [];
for (let sample = 0; sample < 3; sample++) {
  // Alternate order to reduce consistent first-run/order bias.
  for (const policy of sample % 2 ? ['critical-path', 'fifo'] : ['fifo', 'critical-path']) {
    const result = await runJobs(jobs, { policy, concurrency: 2,
      invoke: job => delay(job.estimated_s * 1000),
    });
    runs.push({ sample: sample + 1, policy, duration_ms: result.duration_ms,
      start_order: result.events.filter(e => e.type === 'start').map(e => e.id) });
  }
}
const summaries = ['fifo', 'critical-path'].map(policy => {
  const values = runs.filter(r => r.policy === policy).map(r => r.duration_ms).sort((a, b) => a - b);
  return { policy, n: values.length, min_ms: values[0], median_ms: values[1], max_ms: values[2] };
});
const artifact = { recorded_at: new Date().toISOString(), node: process.version,
  concurrency: 2, jobs, runs, summaries,
  caveats: [
    'Synthetic fixed timer delays; this workload deliberately favors opening a long dependency chain.',
    'Three samples per policy, same process; timer jitter, startup/JIT and host load are not controlled.',
    'Measures scheduler makespan only; excludes model request, tool argument generation, network, and process startup.',
    'No claim about Codex Desktop/backend performance or whole-task speedup; critical path is a heuristic, not an optimal schedule.',
  ],
};
await writeFile(new URL('./benchmark-results.json', import.meta.url), JSON.stringify(artifact, null, 2) + '\n');
console.log(JSON.stringify(artifact, null, 2));
