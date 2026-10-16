"""Compute job counts and timing metrics from stored job records."""
from datetime import datetime
from statistics import mean

from database import connect


def seconds_between(start, end):
    if not start or not end:
        return None
    return max(0.0, (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())


def get_metrics(path=None):
    """Return a snapshot. Only completed/failed jobs count as finished work."""
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT status, created_at, started_at, finished_at FROM jobs"
        ).fetchall()

    statuses = ("pending", "running", "completed", "failed", "canceled")
    counts = {status: 0 for status in statuses}
    wait_times = []
    run_times = []
    finished = []
    first_created = None

    for job in rows:
        counts[job["status"]] += 1
        created = datetime.fromisoformat(job["created_at"])
        if first_created is None or created < first_created:
            first_created = created
        wait = seconds_between(job["created_at"], job["started_at"])
        if wait is not None:
            wait_times.append(wait)
        if job["status"] in ("completed", "failed") and job["finished_at"]:
            finished.append(datetime.fromisoformat(job["finished_at"]))
            run = seconds_between(job["started_at"], job["finished_at"])
            if run is not None:
                run_times.append(run)

    terminal = counts["completed"] + counts["failed"]
    duration = (max(finished) - first_created).total_seconds() if finished else 0
    return {
        "total_jobs": len(rows),
        "status_counts": counts,
        "success_rate_percent": round(100 * counts["completed"] / terminal, 2) if terminal else None,
        "average_queue_wait_seconds": round(mean(wait_times), 4) if wait_times else None,
        "average_execution_seconds": round(mean(run_times), 4) if run_times else None,
        "throughput_jobs_per_second": round(counts["completed"] / duration, 4) if duration > 0 else None,
    }
