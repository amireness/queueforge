"""SQLite storage and atomic job claiming."""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).with_name("queueforge.db")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def connect(path=None):
    db_path = str(path or os.environ.get("QUEUEFORGE_DB", DEFAULT_DB))
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db(path=None):
    with connect(path) as conn:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        conn.executescript(schema)


def create_job(task_type, payload, priority=5, max_attempts=3, path=None):
    timestamp = now()
    with connect(path) as conn:
        cursor = conn.execute(
            """INSERT INTO jobs (task_type, payload, priority, max_attempts, available_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task_type, json.dumps(payload), priority, max_attempts, timestamp, timestamp),
        )
        return cursor.lastrowid


def get_job(job_id, path=None):
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_jobs(path=None):
    with connect(path) as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM jobs ORDER BY id DESC")]


def claim_next(worker_id, path=None):
    """BEGIN IMMEDIATE ensures two workers cannot claim the same pending job."""
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """SELECT id FROM jobs
               WHERE status = 'pending' AND available_at <= ?
               ORDER BY priority ASC, created_at ASC, id ASC LIMIT 1""",
            (now(),),
        ).fetchone()
        if not row:
            conn.commit()
            return None
        conn.execute(
            """UPDATE jobs SET status = 'running', worker_id = ?,
               started_at = ?, attempts = attempts + 1 WHERE id = ?""",
            (worker_id, now(), row["id"]),
        )
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (row["id"],)).fetchone()
        conn.commit()
        return dict(job)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def finish_job(job_id, worker_id, result, path=None):
    with connect(path) as conn:
        conn.execute(
            """UPDATE jobs SET status = 'completed', result = ?, finished_at = ?, error = NULL
               WHERE id = ? AND status = 'running' AND worker_id = ?""",
            (json.dumps(result), now(), job_id, worker_id),
        )


def fail_job(job, worker_id, error, path=None):
    should_retry = job["attempts"] < job["max_attempts"]
    delay_seconds = 2 ** job["attempts"] if should_retry else 0
    available = (datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)).isoformat(timespec="microseconds")
    with connect(path) as conn:
        conn.execute(
            """UPDATE jobs SET status = ?, error = ?, available_at = ?,
               worker_id = NULL, started_at = NULL, finished_at = ?
               WHERE id = ? AND status = 'running' AND worker_id = ?""",
            ("pending" if should_retry else "failed", str(error)[:1000], available,
             None if should_retry else now(), job["id"], worker_id),
        )


def cancel_job(job_id, path=None):
    with connect(path) as conn:
        cursor = conn.execute(
            "UPDATE jobs SET status = 'canceled', finished_at = ? WHERE id = ? AND status = 'pending'",
            (now(), job_id),
        )
        return cursor.rowcount > 0
