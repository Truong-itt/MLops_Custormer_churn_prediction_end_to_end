# Student-Friendly MLOps Stack (Docker Compose Only)

This stack is a simplified architecture for Customer Churn Prediction.

## Services

- `postgres`: metadata database for Airflow and MLflow.
- `mlflow`: experiment tracking and model registry.
- `airflow-webserver`, `airflow-scheduler`: orchestration.
- `fastapi`: online inference API.

No Kubernetes, no Kafka, no Spark, no MinIO.

## Start

```bash
cd infra/docker/student
docker compose up --build -d
```

## Access

- Airflow: http://localhost:8080 (`airflow` / `airflow`)
- MLflow: http://localhost:5000
- FastAPI: http://localhost:8000/docs

## Trigger DAG

1. Open Airflow UI.
2. Enable DAG `churn_batch_pipeline`.
3. Trigger manually.

## Input Data Source

The DAG reads local file:

`/opt/project/data-pipeline/data/Newdata/Telco_customer_churn.xlsx`

(mapped from workspace path via volume mount).

## Main Outputs

- Raw ingest: `data-pipeline/data/raw/telco_customer_churn.xlsx`
- Processed: `data-pipeline/data/processed/churn_processed.csv`
- Features: `data-pipeline/data/processed/churn_features.csv`
- Run metadata: `model_pipeline/src/artifacts/latest_run.json`
- Metrics: `model_pipeline/src/artifacts/latest_metrics.json`
- Rollout status: `model_pipeline/src/artifacts/deploy_status.json`
- Inference log: FastAPI volume at `/app/logs/inference_log.jsonl`
