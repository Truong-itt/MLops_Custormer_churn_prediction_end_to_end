# Student-Friendly MLOps Stack (Docker Compose)

This is the active runtime stack for the cleaned project.

## Architecture

Services:
- postgres
- mlflow
- airflow-webserver
- airflow-scheduler
- fastapi
- evidently-ui

This architecture is intentionally simple:
- No Kubernetes
- No Kafka
- No Spark
- No MinIO

## Start the Stack

```bash
cd infra/docker/student
docker compose up --build -d
```

## Stop the Stack

```bash
cd infra/docker/student
docker compose down
```

## Access URLs

- Airflow: http://localhost:8080
  - username: airflow
  - password: airflow
- MLflow: http://localhost:5000
- FastAPI dashboard and API: http://localhost:8000
- FastAPI docs: http://localhost:8000/docs
- Evidently UI: http://localhost:8001

## End-to-End Flow

1. Place source file at:
   - data-pipeline/data/Newdata/Telco_customer_churn.xlsx
2. Trigger DAG `churn_batch_pipeline` in Airflow.
3. DAG runs ingest, validate, preprocess, feature build, train, evaluate, register, deploy, and monitor steps.
4. FastAPI reloads the production model automatically in deploy step.
5. Drift report is generated and published to Evidently UI.

## Key Outputs

- data-pipeline/data/raw/telco_customer_churn.xlsx
- data-pipeline/data/processed/churn_processed.csv
- data-pipeline/data/processed/churn_features.csv
- model_pipeline/src/artifacts/latest_run.json
- model_pipeline/src/artifacts/latest_metrics.json
- model_pipeline/src/artifacts/deploy_status.json
- serving_pipeline/simple_api/logs/inference_log.jsonl
- serving_pipeline/simple_api/reports/drift_report.html
- serving_pipeline/simple_api/reports/drift_summary.json

## Monitoring Surfaces

- FastAPI monitoring endpoint:
  - GET /monitoring
- Evidently UI project dashboard:
  - http://localhost:8001

## Common Commands

```bash
# Check service status
cd infra/docker/student
docker compose ps

# Tail Airflow scheduler logs
cd infra/docker/student
docker compose logs -f airflow-scheduler

# Tail FastAPI logs
cd infra/docker/student
docker compose logs -f fastapi

# Tail Evidently UI logs
cd infra/docker/student
docker compose logs -f evidently-ui
```

## Troubleshooting

- If DAG is skipped due unchanged source, trigger with force run config in Airflow:
  - {"force_run": true}
- If model is not reloaded, call:
  - POST http://localhost:8000/reload-model
- If Evidently looks empty, rerun DAG to regenerate and republish reports.
