"""Small repeatable local throughput experiment (not a production load test)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import create_job, init_db  # noqa: E402
from metrics import get_metrics  # noqa: E402
from worker import run_once  # noqa: E402

JOB_COUNT = 100


def bench(worker_count):
    with TemporaryDirectory() as directory:
        db = Path(directory) / "bench.db"
        init_db(db)
        for i in range(JOB_COUNT):
            create_job("add_numbers", {"a": i, "b": 1}, path=db)

        def drain(worker_id):
            while run_once(f"bench-{worker_id}", db):
                pass

        started = perf_counter()
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            list(pool.map(drain, range(worker_count)))
        duration = perf_counter() - started
        completed = get_metrics(db)["status_counts"]["completed"]
        return completed, duration


if __name__ == "__main__":
    print("Workers | Completed | Elapsed (s) | Jobs/s")
    for workers in (1, 2, 4):
        completed, elapsed = bench(workers)
        print(f"{workers:>7} | {completed:>9} | {elapsed:>11.3f} | {completed / elapsed:>6.2f}")
