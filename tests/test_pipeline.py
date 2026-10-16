
"""Tests for the running data pipeline."""

import csv
from pathlib import Path

from tasks import load_runs, analyze_runs, generate_report


def test_running_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    data_dir = Path("data")
    data_dir.mkdir()

    with (data_dir / "runs.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "distance_km", "duration_min"])
        writer.writerow(["2026-10-01", 5, 30])
        writer.writerow(["2026-10-03", 10, 58])
        writer.writerow(["2026-10-05", 7, 42])
        writer.writerow(["2026-10-08", 12, 72])

    loaded = load_runs({})
    analyzed = analyze_runs({})
    report = generate_report({})

    assert loaded["count"] == 4
    assert analyzed["total_distance_km"] == 34
    assert analyzed["total_duration_min"] == 202
    assert analyzed["average_pace_min_per_km"] == 5.94
    assert "34.0 km" in report["report"]
