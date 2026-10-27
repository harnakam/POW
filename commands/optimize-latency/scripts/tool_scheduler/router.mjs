import { runJobs } from './scheduler.mjs';

/** Automatically route calls made through an injected tools proxy. */
export async function runToolTasks(tasks, { tools, taskConcurrency = 3, toolConcurrency = 3, onEvent, signal, policy } = {}) {
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
