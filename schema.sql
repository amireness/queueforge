PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'canceled')),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    available_at TEXT NOT NULL,
    worker_id TEXT,
    started_at TEXT,
    lease_until TEXT,
    finished_at TEXT,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_ready
ON jobs(status, available_at, priority, created_at);


CREATE TABLE IF NOT EXISTS job_dependencies (
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    depends_on_id INTEGER NOT NULL REFERENCES jobs(id),
    PRIMARY KEY (job_id, depends_on_id),
    CHECK (job_id != depends_on_id)
);
CREATE INDEX IF NOT EXISTS idx_dependencies_parent ON job_dependencies(depends_on_id);
