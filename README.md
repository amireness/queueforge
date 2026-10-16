
# QueueForge

A lightweight background job processing system built with Python, Flask, and SQLite.

Users submit jobs through a REST API, and workers execute them in the background. QueueForge supports priority scheduling, job dependencies, automatic retries, worker crash recovery, and performance monitoring.

## Technologies

- **Language:** Python
- **API:** Flask
- **Database:** SQLite
- **Testing:** pytest, GitHub Actions
- **Benchmarking:** Python threading, time

## Project Structure

```text
queueforge/
├── app.py                  # REST API
├── database.py             # Database operations
├── scheduler.py            # Priority scheduling
├── worker.py               # Background job execution
├── tasks.py                # Supported task handlers
├── metrics.py              # Performance calculations
├── schema.sql              # Database schema
├── benchmarks/
│   └── compare_workers.py
├── tests/
│   ├── test_queueforge.py
│   ├── test_dependencies.py
│   └── test_metrics.py
├── requirements.txt
└── README.md
```

## How It Works

1. A client submits a job through the Flask API.
2. SQLite stores the job with its priority, status, and dependencies.
3. Workers claim available jobs based on priority and submission order.
4. A job runs only after all its dependencies are completed.
5. The worker executes the task and stores the result.
6. Failed jobs are retried, and abandoned jobs can be recovered.

Lower numeric priorities run first (1 is higher priority than 2).

## Setup

Clone the repository:

```bash
git clone https://github.com/amireness/queueforge.git
cd queueforge
```

Create a virtual environment (Git Bash on Windows):

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

Start the API:

```bash
python app.py
```

The server runs at `http://127.0.0.1:5001`.

Open another terminal and start a worker:

```bash
cd queueforge
source .venv/Scripts/activate
python worker.py
```

Multiple workers can run in separate terminals.

## API Examples

Submit a job:

```bash
curl -X POST http://127.0.0.1:5001/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_type":"add_numbers","payload":{"a":7,"b":5},"priority":1}'
```

Check job status:

```bash
curl http://127.0.0.1:5001/jobs/1
```

Submit a dependent job:

```bash
curl -X POST http://127.0.0.1:5001/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_type":"uppercase","payload":{"text":"hello"},"depends_on":[1]}'
```

The dependent job waits until Job 1 completes successfully.

View performance metrics:

```bash
curl http://127.0.0.1:5001/metrics
```

## Design Decisions

- **SQLite:** Persists jobs and results across application restarts.
- **Atomic claiming:** Uses `BEGIN IMMEDIATE` transactions to prevent multiple workers from claiming the same job.
- **Priority scheduling:** Executes the highest-priority available jobs first, using submission order to break ties.
- **Dependencies:** Stores job relationships in a separate table and checks for circular dependencies.
- **Failure handling:** Retries failed jobs using exponential backoff, up to the configured attempt limit.
- **Crash recovery:** Uses 30-second leases to detect and recover abandoned jobs.
- **Task registry:** Workers execute predefined tasks instead of arbitrary user-provided code.

## Testing

Run all tests:

```bash
python -m pytest -v
```

The project includes 20 automated tests covering API operations, priority scheduling, concurrent claiming, retries, crash recovery, dependencies, cycle detection, and performance metrics.

GitHub Actions runs the test suite on repository updates.

## Performance Benchmark

The benchmark compares 1, 2, and 4 concurrent worker threads processing 100 lightweight arithmetic jobs.

Run:

```bash
python benchmarks/compare_workers.py
```

### Results

Measured on Windows using Python 3.14 and SQLite.

| Workers | Jobs Completed | Time (s) | Jobs/s |
|---------|----------------|----------|--------|
| 1       | 100            | 1.421    | 70.35  |
| 2       | 100            | 2.034    | 49.17  |
| 4       | 100            | 2.757    | 36.27  |

All configurations completed 100 jobs successfully.

For this workload, adding workers reduced throughput. The tasks are small, so worker coordination and SQLite contention may outweigh the benefits of concurrency.

These results come from one benchmark run. The benchmark uses threads, not separate worker processes, and does not represent production capacity.

## Limitations

- Designed for local execution, not multi-host deployment.
- SQLite may become a bottleneck under heavier concurrent workloads.
- Workers use fixed 30-second leases without periodic renewal.
- Jobs may execute more than once after failures, so task handlers should be idempotent.
- Cancellation applies to pending jobs, not actively running jobs.
- The API has no authentication and should only be used locally.

## Future Improvements

- Add lease renewal for long-running jobs.
- Benchmark CPU-bound and I/O-bound workloads separately.
- Add a lightweight monitoring dashboard.
- Evaluate PostgreSQL and Redis for larger deployments.

