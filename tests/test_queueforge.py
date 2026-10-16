import threading
from datetime import datetime, timedelta, timezone
from database import connect, recover_expired_jobs

import pytest

from app import create_app
from database import claim_next, create_job, get_job, init_db
from worker import run_once


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


def test_api_submit_and_complete(db):
    client = create_app(db).test_client()
    response = client.post("/jobs", json={"task_type": "add_numbers", "payload": {"a": 7, "b": 5}})
    assert response.status_code == 201
    job_id = response.get_json()["job_id"]
    assert run_once("worker-test", db)
    result = client.get(f"/jobs/{job_id}").get_json()
    assert result["status"] == "completed"
    assert result["result"] == {"sum": 12}


def test_priority_order(db):
    low = create_job("uppercase", {"text": "a"}, priority=9, path=db)
    high = create_job("uppercase", {"text": "b"}, priority=1, path=db)
    assert claim_next("w1", db)["id"] == high
    assert claim_next("w2", db)["id"] == low


def test_concurrent_claim_is_unique(db):
    job_id = create_job("uppercase", {"text": "hello"}, path=db)
    claimed = []
    barrier = threading.Barrier(2)

    def runner(worker):
        barrier.wait()
        claimed.append(claim_next(worker, db))

    threads = [threading.Thread(target=runner, args=(f"w{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(job is not None for job in claimed) == 1
    assert [job["id"] for job in claimed if job] == [job_id]


def test_failed_job_retries_then_fails(db):
    job_id = create_job("uppercase", {}, max_attempts=1, path=db)
    assert run_once("worker-test", db)
    job = get_job(job_id, db)
    assert job["status"] == "failed"
    assert job["attempts"] == 1


def test_cancel_and_reject_invalid_input(db):
    client = create_app(db).test_client()
    assert client.post("/jobs", json={"task_type": "unknown"}).status_code == 400
    created = client.post("/jobs", json={"task_type": "uppercase", "payload": {"text": "hey"}}).get_json()
    job_id = created["job_id"]
    assert client.post(f"/jobs/{job_id}/cancel").status_code == 200
    assert get_job(job_id, db)["status"] == "canceled"


def test_crashed_worker_job_is_recovered(db):
    job_id = create_job("add_numbers", {"a": 2, "b": 3}, path=db)
    assert claim_next("crashed-worker", db)["id"] == job_id
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with connect(db) as conn:
        conn.execute("UPDATE jobs SET lease_until = ? WHERE id = ?", (past, job_id))
    assert recover_expired_jobs(db) == 1
    assert run_once("replacement-worker", db)
    job = get_job(job_id, db)
    assert job["status"] == "completed"
    assert job["worker_id"] == "replacement-worker"
    assert job["attempts"] == 2


def test_expired_job_with_no_attempts_left_fails(db):
    job_id = create_job("uppercase", {"text": "hi"}, max_attempts=1, path=db)
    claim_next("crashed-worker", db)
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with connect(db) as conn:
        conn.execute("UPDATE jobs SET lease_until = ? WHERE id = ?", (past, job_id))
    assert recover_expired_jobs(db) == 1
    assert get_job(job_id, db)["status"] == "failed"
    assert claim_next("another-worker", db) is None


def test_existing_database_is_migrated(db):
    init_db(db)
    with connect(db) as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
    assert "lease_until" in columns
