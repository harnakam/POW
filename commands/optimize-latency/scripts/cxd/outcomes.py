"""Small, non-retrying failure records shared by command and hook outcomes."""


def failure(kind, *, exit_code=None, evidence_path=None, job_id=None, next_action=None):
    """Describe an observed cause without including command output or exceptions."""
    value = {'kind': kind, 'retryable': False, 'exitCode': exit_code,
             'evidencePath': str(evidence_path) if evidence_path is not None else None}
    if job_id is not None:
        value['jobId'] = job_id
    if next_action is not None:
        value['nextAction'] = next_action
    return value


def summary_failure(jobs, evidence_path=None):
    """Keep the original job cause; blocked dependants are secondary evidence."""
    failed = [(name, job) for name, job in jobs.items() if job.get('status') != 'completed']
    if not failed:
        return None
    name, job = next(((name, job) for name, job in failed
                      if job.get('status') != 'blocked'), failed[0])
    observed = job.get('failure')
    if isinstance(observed, dict):
        return {**observed, 'jobId': name}
    # Old or incomplete results do not prove cancellation or a command exit.
    kinds = {'timed_out': 'timeout', 'cancelled': 'cancelled', 'blocked': 'dependency-blocked'}
    return failure(kinds.get(job.get('status'), 'unknown-failure'),
                   exit_code=job.get('returncode'),
                   evidence_path=job.get('stderr_path') or evidence_path, job_id=name)
