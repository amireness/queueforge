
"""Allowed background tasks. No user-supplied code is executed."""

import csv
import time
from pathlib import Path


def add_numbers(payload):
    a = payload["a"]
    b = payload["b"]
    if not isinstance(a, (int, float)) or isinstance(a, bool):
        raise ValueError("a must be a number")
    if not isinstance(b, (int, float)) or isinstance(b, bool):
        raise ValueError("b must be a number")
    return {"sum": a + b}


def uppercase(payload):
    value = payload["text"]
    if not isinstance(value, str):
        raise ValueError("text must be a string")
    return {"text": value.upper()}


def pause(payload):
    seconds = payload["seconds"]
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not 0 <= seconds <= 5:
        raise ValueError("seconds must be between 0 and 5")
    time.sleep(seconds)
    return {"slept_seconds": seconds}


def load_runs(payload):
    path = Path("data") / "runs.csv"

    with path.open(newline="", encoding="utf-8") as file:
        runs = list(csv.DictReader(file))

    return {"count": len(runs)}


def analyze_runs(payload):
    path = Path("data") / "runs.csv"

    with path.open(newline="", encoding="utf-8") as file:
        runs = list(csv.DictReader(file))

    if not runs:
        raise ValueError("No runs found")

    distance = sum(float(run["distance_km"]) for run in runs)
    duration = sum(float(run["duration_min"]) for run in runs)

    if distance <= 0:
        raise ValueError("Total distance must be positive")

    return {
        "total_distance_km": round(distance, 2),
        "total_duration_min": round(duration, 2),
        "average_pace_min_per_km": round(duration / distance, 2)
    }


def generate_report(payload):
    results = analyze_runs(payload)

    return {
        "report": (
            f"Total distance: {results['total_distance_km']} km, "
            f"total time: {results['total_duration_min']} minutes, "
            f"average pace: {results['average_pace_min_per_km']} min/km"
        )
    }


TASKS = {
    "add_numbers": add_numbers,
    "uppercase": uppercase,
    "pause": pause,
    "load_runs": load_runs,
    "analyze_runs": analyze_runs,
    "generate_report": generate_report,
}

