"use strict";

const performance = { now: () => Date.now() };

// Source: scheduler.mjs

function keys(value, label) {
  if (!Array.isArray(value) || value.some(k => typeof k !== 'string' || !k.trim()) || new Set(value).size !== value.length) {
    throw new TypeError(`${label} must be an array of unique nonempty strings`);
  }
  return [...value];
}

function prepare(jobs) {
  if (!Array.isArray(jobs)) throw new TypeError('jobs must be an array');
  const nodes = jobs.map((job, index) => {
    if (!job || typeof job.id !== 'string' || !job.id.trim()) throw new TypeError('job id must be a nonempty string');
    const estimate = job.estimated_s ?? 1;
    if (!Number.isFinite(estimate) || estimate <= 0) throw new TypeError(`${job.id}: estimated_s must be finite and positive`);
    return {
      job: { ...job }, id: job.id, index, estimate,
      dependencies: keys(job.depends_on ?? [], `${job.id}.depends_on`),
      reads: new Set(keys(job.reads ?? [], `${job.id}.reads`)),
      writes: new Set(keys(job.writes ?? [], `${job.id}.writes`)),
      children: [], status: 'pending',
    };
  });
  const byId = new Map(nodes.map(n => [n.id, n]));
  if (byId.size !== nodes.length) throw new TypeError('duplicate job id');
  for (const node of nodes) for (const id of node.dependencies) {
    const dependency = byId.get(id);
    if (!dependency) throw new TypeError(`${node.id}: unknown dependency ${id}`);
    dependency.children.push(node);
  }
  // Iterative topological traversal also supports large graphs without recursion.
  const remaining = new Map(nodes.map(n => [n, n.dependencies.length]));
  const ready = nodes.filter(n => remaining.get(n) === 0); const ordered = [];
  for (let i = 0; i < ready.length; i++) {
    const node = ready[i]; ordered.push(node);
    for (const child of node.children) {
      remaining.set(child, remaining.get(child) - 1);
      if (remaining.get(child) === 0) ready.push(child);
    }
  }
  if (ordered.length !== nodes.length) throw new TypeError('dependency cycle');
  for (const node of ordered.reverse()) {
    node.priority = node.estimate + node.children.reduce((max, child) => Math.max(max, child.priority), 0);
    if (!Number.isFinite(node.priority)) throw new TypeError('critical-path estimate overflow');
  }
  return { nodes, byId };
}

function conflicts(a, b) {
  return [...a.writes].some(key => b.writes.has(key) || b.reads.has(key)) ||
    [...a.reads].some(key => b.writes.has(key));
}

/** Schedule an entirely validated graph. Adapters own permissions and side effects. */
async function runJobs(jobs, { invoke, concurrency = 4, policy = 'critical-path', signal, onEvent } = {}) {
  if (typeof invoke !== 'function') throw new TypeError('invoke must be a function');
  if (!Number.isSafeInteger(concurrency) || concurrency < 1) throw new TypeError('concurrency must be a positive safe integer');
  if (!['fifo', 'critical-path'].includes(policy)) throw new TypeError('unknown scheduling policy');
  if (signal !== undefined && !(signal instanceof AbortSignal)) throw new TypeError('signal must be an AbortSignal');
  if (onEvent !== undefined && typeof onEvent !== 'function') throw new TypeError('onEvent must be a function');
  const { nodes, byId } = prepare(jobs);
  const origin = performance.now(); const events = []; const running = new Map();
  const observer_errors = []; const observers = [];
  const event = (type, node, extra = {}) => {
    const entry = { type, id: node.id, at_ms: performance.now() - origin, ...extra };
    events.push(entry);
    if (!onEvent) return;
    const recordError = error => observer_errors.push({ type, id: node.id,
      error: { name: error?.name ?? 'Error', message: error?.message ?? String(error) } });
    try {
      // A separate copy protects the scheduler's event record from observer mutation.
      const value = onEvent(structuredClone(entry));
      if (value !== undefined) observers.push(Promise.resolve(value).catch(recordError));
    } catch (error) { recordError(error); }
  };
  const block = (node, reason, dependencies = []) => {
    node.status = 'blocked'; node.reason = reason; node.blocked_by = dependencies;
    node.ended_ms = performance.now() - origin;
    event('blocked', node, { reason, blocked_by: dependencies });
  };
  while (nodes.some(n => n.status === 'pending') || running.size) {
    // Iterate until failure propagation reaches every descendant, regardless of input order.
    let changed;
    do {
      changed = false;
      for (const node of nodes.filter(n => n.status === 'pending')) {
        const failed = node.dependencies.filter(id => ['failed', 'blocked'].includes(byId.get(id).status));
        if (signal?.aborted || failed.length) {
          block(node, signal?.aborted ? 'cancelled' : 'dependency-failed', failed); changed = true;
        }
      }
    } while (changed);
    const candidates = nodes.filter(n => n.status === 'pending' && n.dependencies.every(id => byId.get(id).status === 'completed'));
    candidates.sort((a, b) => (policy === 'critical-path' ? b.priority - a.priority : 0) || a.index - b.index);
    for (const node of candidates) {
      if (running.size >= concurrency) break;
      if (signal?.aborted) break;
      if ([...running.keys()].some(other => conflicts(node, other))) continue;
      node.status = 'running'; node.started_ms = performance.now() - origin; event('start', node);
      const task = Promise.resolve().then(() => invoke(node.job, { signal })).then(
        value => { node.status = 'completed'; node.value = value; },
        error => { node.status = 'failed'; node.error = { name: error?.name ?? 'Error', message: error?.message ?? String(error) }; },
      ).then(() => {
        node.ended_ms = performance.now() - origin; node.duration_ms = node.ended_ms - node.started_ms;
        event(node.status, node, node.error ? { error: node.error } : {});
        running.delete(node);
      });
      running.set(node, task);
    }
    if (running.size) await Promise.race(running.values());
  }
  const duration_ms = performance.now() - origin;
  await Promise.all(observers);
  return {
    policy, concurrency, duration_ms, events, observer_errors,
    jobs: nodes.map(n => ({ id: n.id, status: n.status, started_ms: n.started_ms ?? null,
      ended_ms: n.ended_ms, duration_ms: n.duration_ms ?? null,
      ...(n.status === 'completed' ? { value: n.value } : {}),
      ...(n.error ? { error: n.error } : {}),
      ...(n.reason ? { reason: n.reason, blocked_by: n.blocked_by } : {}),
    })),
  };
}

// Source: tasks.mjs

/** Run multiple local job graphs through one global concurrency/resource pool. */
async function runTasks(tasks, { invoke, onEvent, ...options } = {}) {
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

// Source: router.mjs

/** Automatically route calls made through an injected tools proxy. */
async function runToolTasks(tasks, { tools, taskConcurrency = 3, toolConcurrency = 3, onEvent, signal, policy } = {}) {
  if (!Array.isArray(tasks)) throw new TypeError('tasks must be an array');
  if (!tools || (typeof tools !== 'object' && typeof tools !== 'function')) throw new TypeError('tools must be an object');
  if (!Number.isSafeInteger(toolConcurrency) || toolConcurrency < 1) throw new TypeError('toolConcurrency must be a positive safe integer');
  if (onEvent !== undefined && typeof onEvent !== 'function') throw new TypeError('onEvent must be a function');
  for (const task of tasks) if (!task || typeof task.run !== 'function') throw new TypeError('every task needs a run function');
  let active = 0; const queue = []; const tool_events = []; const observer_errors = []; const observers = [];
  const origin = Date.now();
  const emit = entry => {
    const event = { ...entry, at_ms: Date.now() - origin }; tool_events.push(event);
    if (!onEvent) return;
    const failed = error => observer_errors.push({ taskId: entry.taskId, tool: entry.tool,
      error: { name: error?.name ?? 'Error', message: error?.message ?? String(error) } });
    try { observers.push(Promise.resolve(onEvent({ ...event })).catch(failed)); } catch (error) { failed(error); }
  };
  const acquire = () => new Promise(resolve => {
    const enter = () => { active++; resolve(() => { active--; queue.shift()?.(); }); };
    if (active < toolConcurrency) enter(); else queue.push(enter);
  });
  const result = await runJobs(tasks, {
    concurrency: taskConcurrency, signal, ...(policy === undefined ? {} : { policy }),
    invoke: async task => {
      let tail = Promise.resolve(); const captured = []; let open = true;
      const proxy = new Proxy(tools, { get(target, name) {
        const method = Reflect.get(target, name, target);
        if (typeof method !== 'function') return method;
        return (...args) => {
          if (!open) return Promise.reject(new Error('task callback has already returned'));
          const call = tail.then(async () => {
            const release = await acquire();
            emit({ type: 'start', taskId: task.id, tool: String(name) });
            try {
              const value = await Reflect.apply(method, target, args);
              emit({ type: 'end', status: 'completed', taskId: task.id, tool: String(name) });
              return value;
            } catch (error) {
              emit({ type: 'end', status: 'failed', taskId: task.id, tool: String(name) }); throw error;
            } finally { release(); }
          });
          // Attach rejection handlers immediately, including for forgotten awaits.
          tail = call.catch(() => {}); captured.push(call); return call;
        };
      } });
      let value; let callbackError; let callbackFailed = false;
      try { value = await task.run(proxy, { signal }); }
      catch (error) { callbackError = error; callbackFailed = true; }
      finally { open = false; }
      const calls = await Promise.allSettled(captured);
      if (callbackFailed) throw callbackError;
      const failed = calls.find(call => call.status === 'rejected');
      if (failed) throw failed.reason;
      return value;
    },
  });
  await Promise.all(observers);
  return { ...result, tasks: result.jobs, tool_events, tool_observer_errors: observer_errors };
}

return { runJobs, runTasks, runToolTasks };
