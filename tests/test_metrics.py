"""Phase 4: metrics tests, using isolated databases."""
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from database import connect, create_job, init_db
from metrics import get_metrics
from worker import run_once


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "metrics.db"
    init_db(path)
    return path


def test_empty_metrics(db):
    data = get_metrics(db)
    assert data["total_jobs"] == 0
    assert all(count == 0 for count in data["status_counts"].values())
    assert data["success_rate_percent"] is None
    assert data["throughput_jobs_per_second"] is None


def test_completed_job_metrics(db):
    create_job("add_numbers", {"a": 2, "b": 3}, path=db)
    assert run_once("metrics-worker", db)
    data = get_metrics(db)
    assert data["total_jobs"] == 1
    assert data["status_counts"]["completed"] == 1
    assert data["success_rate_percent"] == 100.0
    assert data["average_queue_wait_seconds"] >= 0
    assert data["average_execution_seconds"] >= 0
    assert data["throughput_jobs_per_second"] is not None


def test_mixed_results_and_endpoint(db):
    create_job("add_numbers", {"a": 1, "b": 1}, path=db)
    create_job("uppercase", {}, max_attempts=1, path=db)
    assert run_once("w", db)
    assert run_once("w", db)
    data = create_app(db).test_client().get("/metrics")
    assert data.status_code == 200
    result = data.get_json()
    assert result["status_counts"]["completed"] == 1
    assert result["status_counts"]["failed"] == 1
    assert result["success_rate_percent"] == 50.0


def test_pending_job_not_counted_as_failure(db):
    create_job("uppercase", {"text": "later"}, path=db)
    result = get_metrics(db)
    assert result["status_counts"]["pending"] == 1
    assert result["success_rate_percent"] is None


def test_wait_uses_timestamps(db):
    job_id = create_job("uppercase", {"text": "a"}, path=db)
    assert run_once("w", db)
    with connect(db) as conn:
        row = conn.execute("SELECT started_at FROM jobs WHERE id = ?", (job_id,)).fetchone()
        started = datetime.fromisoformat(row["started_at"])
        conn.execute("UPDATE jobs SET created_at = ? WHERE id = ?", (
            (started - timedelta(seconds=10)).isoformat(), job_id))
    assert get_metrics(db)["average_queue_wait_seconds"] == 10.0
