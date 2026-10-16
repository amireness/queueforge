
"""Submit a running data pipeline to QueueForge."""

import json
from urllib.request import Request, urlopen

API_URL = "http://127.0.0.1:5001/jobs"


def submit_job(task_type, depends_on=None):
    data = {
        "task_type": task_type,
        "payload": {},
        "priority": 1,
        "depends_on": depends_on or [],
    }

    request = Request(
        API_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request) as response:
        return json.load(response)["job_id"]


def main():
    load_id = submit_job("load_runs")
    analyze_id = submit_job("analyze_runs", [load_id])
    report_id = submit_job("generate_report", [analyze_id])

    print(f"Load data: Job {load_id}")
    print(f"Analyze data: Job {analyze_id}")
    print(f"Generate report: Job {report_id}")


if __name__ == "__main__":
    main()
