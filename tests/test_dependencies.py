import pytest
from app import create_app
from database import add_dependency, cancel_job, claim_next, create_job, get_job, init_db, list_dependencies
from worker import run_once


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "dependencies.db"
    init_db(path)
    return path


def test_dependent_waits_then_runs(db):
    first = create_job("add_numbers", {"a": 1, "b": 2}, path=db)
    second = create_job("uppercase", {"text": "hello"}, priority=1, path=db, dependencies=[first])
    assert claim_next("w", db)["id"] == first
    assert claim_next("other", db) is None
    # Finish parent through actual worker flow in separate test below.
    from database import finish_job
    finish_job(first, "w", {"sum": 3}, db)
    assert run_once("w2", db)
    assert get_job(second, db)["status"] == "completed"


def test_three_job_chain(db):
    a = create_job("uppercase", {"text": "a"}, path=db)
    b = create_job("uppercase", {"text": "b"}, path=db, dependencies=[a])
    c = create_job("uppercase", {"text": "c"}, priority=1, path=db, dependencies=[b])
    assert [list_dependencies(i, db) for i in (a, b, c)] == [[], [a], [b]]
    for job_id in (a, b, c):
        assert run_once("worker", db)
        assert get_job(job_id, db)["status"] == "completed"


def test_missing_parent_and_invalid_api(db):
    client = create_app(db).test_client()
    assert client.post("/jobs", json={"task_type":"uppercase", "depends_on":[999]}).status_code == 400
    assert client.post("/jobs", json={"task_type":"uppercase", "depends_on":[True]}).status_code == 400
    assert client.post("/jobs", json={"task_type":"uppercase", "depends_on":[1,1]}).status_code == 400


def test_cycle_and_self_dependency_rejected(db):
    a = create_job("uppercase", {"text":"a"}, path=db)
    b = create_job("uppercase", {"text":"b"}, path=db)
    c = create_job("uppercase", {"text":"c"}, path=db)
    add_dependency(b, a, db)
    add_dependency(c, b, db)
    with pytest.raises(ValueError, match="Circular"):
        add_dependency(a, c, db)
    with pytest.raises(ValueError, match="itself"):
        add_dependency(a, a, db)


def test_failure_propagates_through_chain(db):
    a = create_job("uppercase", {}, max_attempts=1, path=db)
    b = create_job("uppercase", {"text":"b"}, path=db, dependencies=[a])
    c = create_job("uppercase", {"text":"c"}, path=db, dependencies=[b])
    assert run_once("worker", db)
    assert get_job(a, db)["status"] == "failed"
    assert not run_once("worker", db)
    assert get_job(b, db)["status"] == "failed"
    assert get_job(c, db)["status"] == "failed"


def test_cancel_propagates(db):
    a = create_job("uppercase", {"text":"a"}, path=db)
    b = create_job("uppercase", {"text":"b"}, path=db, dependencies=[a])
    assert cancel_job(a, db)
    assert claim_next("worker", db) is None
    assert get_job(b, db)["status"] == "failed"


def test_detail_includes_dependencies(db):
    client = create_app(db).test_client()
    a = client.post("/jobs", json={"task_type":"uppercase", "payload":{"text":"a"}}).get_json()["job_id"]
    response = client.post("/jobs", json={"task_type":"uppercase", "payload":{"text":"b"}, "depends_on":[a]})
    assert response.status_code == 201
    b = response.get_json()["job_id"]
    assert client.get(f"/jobs/{b}").get_json()["depends_on"] == [a]
