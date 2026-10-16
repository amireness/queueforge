"""QueueForge REST API."""
import json
from flask import Flask, jsonify, request

from database import cancel_job, create_job, get_job, init_db, list_jobs, list_dependencies
from tasks import TASKS


def create_app(db_path=None):
    app = Flask(__name__)
    if db_path is not None:
        app.config["DB_PATH"] = db_path
    init_db(app.config.get("DB_PATH"))

    def db():
        return app.config.get("DB_PATH")

    @app.get("/")
    def index():
        return jsonify({"name": "QueueForge", "endpoints": ["GET /jobs", "POST /jobs", "GET /jobs/<id>", "POST /jobs/<id>/cancel"]})

    @app.post("/jobs")
    def submit():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Expected a JSON object"}), 400
        task_type = data.get("task_type")
        payload = data.get("payload", {})
        priority = data.get("priority", 5)
        max_attempts = data.get("max_attempts", 3)
        dependencies = data.get("depends_on", [])
        if task_type not in TASKS:
            return jsonify({"error": f"task_type must be one of {list(TASKS)}"}), 400
        if not isinstance(payload, dict):
            return jsonify({"error": "payload must be an object"}), 400
        if type(priority) is not int or not 1 <= priority <= 10:
            return jsonify({"error": "priority must be an integer from 1 to 10 (1 highest)"}), 400
        if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
            return jsonify({"error": "max_attempts must be an integer from 1 to 10"}), 400
        if not isinstance(dependencies, list) or any(type(i) is not int or i <= 0 for i in dependencies):
            return jsonify({"error": "depends_on must be a list of positive job IDs"}), 400
        try:
            job_id = create_job(task_type, payload, priority, max_attempts, db(), dependencies)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"job_id": job_id, "status": "pending"}), 201

    @app.get("/jobs")
    def jobs():
        return jsonify([display(job) for job in list_jobs(db())])

    @app.get("/jobs/<int:job_id>")
    def job_detail(job_id):
        job = get_job(job_id, db())
        if job is None:
            return jsonify({"error": "Job not found"}), 404
        result = display(job)
        result["depends_on"] = list_dependencies(job_id, db())
        return jsonify(result)

    @app.post("/jobs/<int:job_id>/cancel")
    def cancel(job_id):
        if not get_job(job_id, db()):
            return jsonify({"error": "Job not found"}), 404
        if not cancel_job(job_id, db()):
            return jsonify({"error": "Only pending jobs can be canceled"}), 409
        return jsonify({"job_id": job_id, "status": "canceled"})

    return app


def display(job):
    job = dict(job)
    for key in ("payload", "result"):
        if job[key] is not None:
            job[key] = json.loads(job[key])
    return job


if __name__ == "__main__":
    create_app().run(port=5001, debug=False)
