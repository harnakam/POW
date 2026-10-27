import { runJobs } from './scheduler.mjs';

/** Run multiple local job graphs through one global concurrency/resource pool. */
export async function runTasks(tasks, { invoke, onEvent, ...options } = {}) {
  if (!Array.isArray(tasks)) throw new TypeError('tasks must be an array');
  if (typeof invoke !== 'function') throw new TypeError('invoke must be a function');
  if (onEvent !== undefined && typeof onEvent !== 'function') throw new TypeError('onEvent must be a function');
  const taskIds = new Set(); const metadata = new Map(); const flattened = [];
  const groups = tasks.map((task, taskIndex) => {
    if (!task || typeof task.id !== 'string' || !task.id.trim()) throw new TypeError('task id must be a nonempty string');
    if (taskIds.has(task.id)) throw new TypeError('duplicate task id');
    taskIds.add(task.id);
    if (task.depends_on !== undefined) throw new TypeError('task-level depends_on is unsupported; use local job dependencies');
    if (!Array.isArray(task.jobs) || task.jobs.length === 0) throw new TypeError(`${task.id}: jobs must be a nonempty array`);
    const localIds = new Map();
    const jobs = task.jobs.map((job, jobIndex) => {
      if (!job || typeof job.id !== 'string' || !job.id.trim()) throw new TypeError('job id must be a nonempty string');
      if (localIds.has(job.id)) throw new TypeError(`${task.id}: duplicate job id`);
      const id = `${taskIndex}:${jobIndex}`;
      localIds.set(job.id, id);
      metadata.set(id, { taskId: task.id, localId: job.id, job: { ...job } });
      return { ...job, id };
    });
    jobs.forEach((job, index) => {
      const dependencies = task.jobs[index].depends_on ?? [];
      if (!Array.isArray(dependencies)) throw new TypeError(`${task.id}: depends_on must be an array`);
      job.depends_on = dependencies.map(id => {
        if (!localIds.has(id)) throw new TypeError(`${task.id}: unknown local dependency ${String(id)}`);
        return localIds.get(id);
      });
      flattened.push(job);
    });
    return { id: task.id, internalIds: jobs.map(job => job.id) };
  });
  const decode = entry => {
    const { taskId, localId } = metadata.get(entry.id);
    return { ...entry, id: localId, taskId,
      ...(entry.blocked_by ? { blocked_by: entry.blocked_by.map(id => metadata.get(id).localId) } : {}),
    };
  };
  const result = await runJobs(flattened, {
    ...options,
    invoke: (job, context) => {
      const { taskId, localId, job: original } = metadata.get(job.id);
      return invoke(original, { ...context, taskId, localId });
    },
    ...(onEvent ? { onEvent: event => onEvent(decode(event)) } : {}),
  });
  const jobsById = new Map(result.jobs.map(job => [job.id, job]));
  const events = result.events.map(decode);
  const grouped = groups.map(group => {
    const jobs = group.internalIds.map(id => decode(jobsById.get(id)));
    const status = jobs.some(job => job.status === 'failed') ? 'failed'
      : jobs.some(job => job.status === 'blocked') ? 'blocked' : 'completed';
    return { id: group.id, status, jobs, events: events.filter(event => event.taskId === group.id) };
  });
  return { ...result, jobs: result.jobs.map(decode), events,
    observer_errors: result.observer_errors.map(decode), tasks: grouped };
}
