# Docker Infrastructure

This directory contains Docker-based infrastructure options.

## Student Stack (Recommended)

Use:
- `infra/docker/student/docker-compose.yml`

This stack runs locally with:
- Airflow
- MLflow
- PostgreSQL
- FastAPI
- Gradio
- Evidently UI
- MinIO

### Quick Start

```bash
cd infra/docker/student
docker compose up -d --build
```

### URLs

- Airflow: http://localhost:8080
- MLflow: http://localhost:5000
- FastAPI docs: http://localhost:8000/docs
- FastAPI dashboard: http://localhost:8000
- Gradio: http://localhost:7860
- Evidently UI: http://localhost:8001
- MinIO Console: http://localhost:9001

### Behavior Notes

- MLflow artifacts are stored in MinIO bucket `mlflow`.
- DAG task `check_new_data` controls whether training flow continues.
- Structured run/task logs are written to:
	- `infra/docker/student/logs/task_events.jsonl`
	- `infra/docker/student/logs/run_summaries/*.json`
See infra/docker/student/README.md for full run workflow and troubleshooting.
