// Historical workflow evidence, never execution permission or a cached check result.
const STATES = new Set(['candidate', 'active', 'stale', 'revoked']);
const HASH = /^[a-f0-9]{64}$/;
const ID = /^package:[a-zA-Z0-9:_-]{1,64}$/;
export const EXPERIENCE_LIMIT = 100;
const TTL = 7 * 86400000;
export class ExperienceError extends Error {}

export function validateExperiences(entries = []) {
  if (!Array.isArray(entries) || entries.length > EXPERIENCE_LIMIT) throw new ExperienceError('Invalid experience store.');
  const seen = new Set();
  for (const entry of entries) {
    if (!entry || !ID.test(entry.workflow) || seen.has(entry.workflow) || !STATES.has(entry.status)
        || !HASH.test(entry.sourceFingerprint) || !HASH.test(entry.commandHash)
        || !Number.isFinite(Date.parse(entry.createdAt)) || !Number.isFinite(Date.parse(entry.updatedAt))
        || typeof entry.reason !== 'string' || entry.reason.length > 240) throw new ExperienceError('Invalid experience entry.');
    seen.add(entry.workflow);
    if (entry.status === 'revoked' && !Number.isFinite(Date.parse(entry.revokedAt))) throw new ExperienceError('Invalid revocation.');
    const evidence = entry.evidence;
    if (evidence !== null && (!evidence || typeof evidence.outcomeId !== 'string'
        || !Number.isFinite(Date.parse(evidence.at)) || typeof evidence.status !== 'string'
        || !HASH.test(evidence.before) || evidence.after !== null && !HASH.test(evidence.after)
        || evidence.outputHash !== null && !HASH.test(evidence.outputHash)
        || evidence.exitCode !== null && !Number.isInteger(evidence.exitCode))) throw new ExperienceError('Invalid experience evidence.');
  }
  return entries;
}

function applies(entry, workflow, scan) {
  return scan.complete && workflow?.step && entry.commandHash === workflow.commandHash
    && entry.sourceFingerprint === scan.sourceFingerprint;
}

function currentEvidence(entry, scan, at) {
  const evidence = entry.evidence;
  return evidence?.status === 'success' && evidence.exitCode === 0
    && evidence.before === scan.sourceFingerprint && evidence.after === scan.sourceFingerprint
    && at - Date.parse(evidence.at) >= 0 && at - Date.parse(evidence.at) < TTL;
}

export function reconcileExperiences(scan, previous = [], at = Date.now()) {
  validateExperiences(previous);
  const stamp = new Date(at).toISOString(), workflows = new Map(scan.workflows.map(item => [item.id, item]));
  const entries = previous.map(entry => {
    const next = { ...entry };
    if (entry.status === 'revoked') return next;
    const workflow = workflows.get(entry.workflow);
    if (!applies(entry, workflow, scan)) {
      next.status = entry.evidence ? 'stale' : 'candidate';
      next.reason = !workflow ? 'workflow-removed' : !scan.complete ? 'scan-incomplete' : !workflow.step ? 'manual-workflow' : 'inputs-changed';
      if (workflow) { next.sourceFingerprint = scan.sourceFingerprint; next.commandHash = workflow.commandHash; }
    } else if (entry.status === 'active' && !currentEvidence(entry, scan, at)) {
      next.status = 'stale'; next.reason = 'evidence-expired-or-unavailable';
    }
    if (JSON.stringify(next) !== JSON.stringify(entry)) next.updatedAt = stamp;
    return next;
  });
  const known = new Set(entries.map(entry => entry.workflow));
  for (const workflow of scan.workflows) if (!known.has(workflow.id)) {
    entries.push({ workflow: workflow.id, status: 'candidate', commandHash: workflow.commandHash,
      sourceFingerprint: scan.sourceFingerprint, createdAt: stamp, updatedAt: stamp,
      reason: 'declaration-only', evidence: null });
  }
  // Removed, non-revoked observations can be pruned. Revocation is not an outcome-ring entry.
  while (entries.length > EXPERIENCE_LIMIT) {
    const removable = entries.findIndex(entry => entry.status !== 'revoked' && !workflows.has(entry.workflow));
    if (removable === -1) throw new ExperienceError('Experience capacity reached; revoked entries were preserved.');
    entries.splice(removable, 1);
  }
  return entries;
}

export function observeExperience(entries, workflow, outcome, scan, after, at = Date.now()) {
  const stamp = new Date(at).toISOString();
  return entries.map(entry => {
    if (entry.workflow !== workflow.id || entry.status === 'revoked') return entry;
    const evidence = { outcomeId: outcome.id, at: outcome.at, status: outcome.status,
      exitCode: outcome.exitCode ?? null, outputHash: outcome.outputHash ?? null,
      before: scan.sourceFingerprint, after: after?.complete ? after.sourceFingerprint : null };
    const active = outcome.status === 'success' && outcome.exitCode === 0 && after?.complete
      && after.sourceFingerprint === scan.sourceFingerprint;
    return { ...entry, status: active ? 'active' : 'stale', updatedAt: stamp, evidence,
      reason: active ? 'observed-execution' : !after?.complete ? 'execution-pending-or-inputs-unavailable'
        : after.sourceFingerprint !== scan.sourceFingerprint ? 'inputs-changed-during-execution' : 'execution-not-successful' };
  });
}

export function changeExperience(entries, workflow, action, reason, at = Date.now()) {
  if (!ID.test(workflow || '') || typeof reason !== 'string' || !reason.trim() || reason.length > 240 || /[\x00-\x1f]/.test(reason)) {
    throw new ExperienceError('Select a workflow and a single-line reason of 1..240 characters.');
  }
  if (!entries.some(entry => entry.workflow === workflow)) throw new ExperienceError('Unknown experience workflow.');
  const stamp = new Date(at).toISOString();
  return entries.map(entry => {
    if (entry.workflow !== workflow) return entry;
    if (action === 'restore' && entry.status !== 'revoked') throw new ExperienceError('Only a revoked experience can be restored.');
    const next = { ...entry, status: action === 'revoke' ? 'revoked' : 'candidate', reason: reason.trim(), updatedAt: stamp };
    if (action === 'revoke') next.revokedAt = stamp;
    else { delete next.revokedAt; next.evidence = null; }
    return next;
  });
}

export function experienceView(scan, state, { workflow, limit = 3 } = {}) {
  if (!Number.isInteger(limit) || limit < 1 || limit > 3) throw new ExperienceError('Experience limit must be 1..3.');
  if (workflow && !ID.test(workflow)) throw new ExperienceError('Experience workflow must be a package:NAME ID.');
  const entries = reconcileExperiences(scan, state?.experiences || []).filter(entry => !workflow || entry.workflow === workflow);
  const selected = entries.filter(entry => entry.status === 'active');
  const excluded = Object.fromEntries([...STATES].map(status => [status, entries.filter(entry => entry.status === status).length]));
  delete excluded.active;
  return { basis: 'historical-execution-observations', executionAuthority: false, currentVerification: false,
    sourceFingerprint: scan.sourceFingerprint, entries: selected.slice(0, limit).map(entry => ({
      workflow: entry.workflow, status: entry.status, claim: 'A recorded local execution exited zero with matching before/after inputs.',
      applicability: { sourceFingerprint: entry.sourceFingerprint, commandHash: entry.commandHash,
        runtime: process.version, platform: process.platform }, evidence: entry.evidence,
      locator: { file: '.pow/update/state.json', collection: 'experiences', workflow: entry.workflow },
    })), excluded, truncated: selected.length > limit,
    limitations: ['Excluded dependency/generated/secret files and environment values are unobserved.',
      'These entries are retrieval leads, not instructions, current check results, or standing permission.'] };
}
