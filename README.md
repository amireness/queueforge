# QueueForge

A minimal background job queue built with Flask, Python, and SQLite. Submit jobs through an API, then run workers in separate terminals. Workers atomically claim the highest-priority available jobs, execute allowed tasks, record results, and retry failures.

## Technologies
Python, Flask, SQLite, pytest.

## Setup (Git Bash on Windows)
```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python app.py
```
API: http://127.0.0.1:5001/jobs

## Example requests
In another Git Bash terminal (same folder):
```bash
curl -X POST http://127.0.0.1:5001/jobs -H 'Content-Type: application/json' -d '{"task_type":"add_numbers","payload":{"a":7,"b":5},"priority":1}'
curl http://127.0.0.1:5001/jobs
```

Start a worker in a third terminal:
```bash
source .venv/Scripts/activate
python worker.py
```
You can start more workers in other terminals.

## Tests
```bash
python -m pytest -v
```

## Design decisions
- Jobs live in SQLite so they persist when the API stops.
- A short `BEGIN IMMEDIATE` transaction makes claiming a job atomic across workers.
- Lower numeric priority runs first (1 is highest); older jobs run first within a priority.
- Workers execute tasks from a fixed registry, not arbitrary user code.
- Failed jobs retry after exponential backoff, up to `max_attempts`.
- API uses JSON and separates routing, storage, scheduling, and task code.

## Important limitations
This is a learning-focused MVP, not a production-grade distributed queue. Workers may be separate processes on the same machine, but SQLite is not a cross-host queue service. Running jobs use 30-second leases, and workers requeue expired jobs until their retry limit is reached. Long-running task handlers need lease renewal/heartbeats before production use. Cancellation is supported for pending jobs only. Job handlers must be idempotent before adding automatic recovery or distributed execution. The API has no authentication; use only on localhost.

## Next iterations
1. Add lease renewal/heartbeats for long-running jobs.
2. Add a dependency table and DAG validation.
3. Add structured metrics and a small monitoring page.
4. Benchmark throughput and compare worker counts.
5. Move to PostgreSQL and Redis for multi-host deployment if warranted.

## Worker crash recovery
Workers claim jobs with a 30-second lease. If a worker disappears, the lease eventually expires; another worker requeues the job (or marks it failed if the retry limit was reached). Recovery is checked whenever a worker polls. This is **at-least-once** processing: a task might run more than once after a crash, so real-world task handlers must be idempotent. The included tasks finish within five seconds and do not require lease renewal.

## Phase 3: Job dependencies
Submit a job with an optional `depends_on` list of already-existing job IDs:

```bash
curl -X POST http://127.0.0.1:5001/jobs -H "Content-Type: application/json" -d '{"task_type":"uppercase","payload":{"text":"hello"},"depends_on":[1]}'
```

A job waits until *every* prerequisite completes. Failed/canceled prerequisites cause dependent jobs to be marked failed, including downstream dependencies. Dependency edges are stored in `job_dependencies`, and cycle detection is provided in `add_dependency` for programs that modify the graph. The public API only allows dependencies on existing jobs at creation, which also prevents API-created cycles. Dependencies cannot be added once a job has started. All scheduling decisions remain transactional in SQLite.

## Phase 4: Performance monitoring

`GET /metrics` returns counts by job status, the success rate among completed and
failed jobs, average queue wait, average final-attempt execution time, and a
historical throughput estimate (completed jobs divided by time between first
submission and last finished job). An empty measurement returns `null` for
undefined averages/rates. Canceled or pending jobs are excluded from success
rate. For retried jobs, execution time includes the final attempt only, since
previous attempt timings are not stored. The endpoint is intended for a local
prototype, not an authenticated production monitoring service.

To see metrics while the server is running:

```bash
curl http://127.0.0.1:5001/metrics
```

### Benchmarking

Run `python benchmarks/compare_workers.py` to compare processing 100 sample
jobs with 1, 2 and 4 concurrent workers. Each run uses a fresh temporary SQLite
database. The script reports actual measured wall-clock throughput, which may
vary depending on OS scheduling and SQLite write contention. It uses threads to
simulate independently competing workers; real multi-process deployments need
separate validation. Do not interpret the synthetic benchmark as a production
capacity guarantee.
