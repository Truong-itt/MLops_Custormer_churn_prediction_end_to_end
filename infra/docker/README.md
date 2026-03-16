# Docker Infrastructure (Simplified)

This directory now uses a single active stack for the student project:

- student/

Legacy folders from previous architectures were removed from the active workflow.

## Active Stack

Use only:
- infra/docker/student/docker-compose.yml

## Quick Start

```bash
cd infra/docker/student
docker compose up --build -d
```

## Active Services and Ports

- Airflow Web UI: http://localhost:8080
- MLflow UI: http://localhost:5000
- FastAPI API and dashboard: http://localhost:8000
- Evidently UI: http://localhost:8001

## Stop

```bash
cd infra/docker/student
docker compose down
```

## Notes

This simplified project intentionally does not use Kubernetes, Kafka, Spark, or MinIO.
See infra/docker/student/README.md for full run workflow and troubleshooting.
