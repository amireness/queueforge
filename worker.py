"""Run workers in separate Git Bash terminals."""
import argparse
import json
import socket
import time
import uuid

from database import fail_job, finish_job, init_db
from scheduler import next_job
from tasks import TASKS


def run_once(worker_id, path=None):
    job = next_job(worker_id, path)
    if job is None:
        return False
    print(f"Worker {worker_id}: running job {job['id']} ({job['task_type']})", flush=True)
    try:
        result = TASKS[job["task_type"]](json.loads(job["payload"]))
    except Exception as exc:
        fail_job(job, worker_id, exc, path)
        print(f"Job {job['id']} failed: {exc}", flush=True)
    else:
        finish_job(job["id"], worker_id, result, path)
        print(f"Job {job['id']} completed: {result}", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process at most one job, then exit")
    parser.add_argument("--poll", type=float, default=1, help="Seconds between empty-queue checks")
    args = parser.parse_args()
    if args.poll <= 0:
        parser.error("--poll must be positive")
    init_db()
    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    print(f"Started {worker_id}. Press Ctrl+C to stop.", flush=True)
    try:
        while True:
            processed = run_once(worker_id)
            if args.once:
                break
            if not processed:
                time.sleep(args.poll)
    except KeyboardInterrupt:
        print("Worker stopped.")


if __name__ == "__main__":
    main()
