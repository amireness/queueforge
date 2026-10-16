"""The scheduling rule: lower priority number runs first, then older jobs."""
from database import claim_next


def next_job(worker_id, path=None):
    return claim_next(worker_id, path)
