# Customer Churn Prediction (Simplified MLOps)

This repository is a student-friendly MLOps project for customer churn prediction.

## Scope

Active stack in this repo:
- Docker Compose
- Airflow (orchestration)
- MLflow (tracking + registry)
- FastAPI (serving)
- Evidently UI (monitoring dashboard)

Removed from active scope:
- Kubernetes
- Kafka
- MinIO
- Spark
- Feast

## Data Source

Main input file:
- data-pipeline/data/Newdata/Telco_customer_churn.xlsx

## Run

```bash
cd infra/docker/student
docker compose up --build -d
```

## UIs

- Airflow: http://localhost:8080
  - username: airflow
  - password: airflow
- MLflow: http://localhost:5000
- FastAPI dashboard: http://localhost:8000
- FastAPI docs: http://localhost:8000/docs
- Evidently UI: http://localhost:8001

## Main Workflow

DAG name: churn_batch_pipeline

Task sequence:
1. check_new_data
2. ingest_raw_data
3. validate_data
4. preprocess_data
5. build_features
6. train_model
7. evaluate_model
8. register_model
9. deploy_model
10. monitor_drift
11. notify_status

## Important Outputs

- data-pipeline/data/raw/telco_customer_churn.xlsx
- data-pipeline/data/processed/churn_processed.csv
- data-pipeline/data/processed/churn_features.csv
- model_pipeline/src/artifacts/latest_run.json
- model_pipeline/src/artifacts/latest_metrics.json
- model_pipeline/src/artifacts/deploy_status.json
- serving_pipeline/simple_api/reports/drift_summary.json
- serving_pipeline/simple_api/reports/drift_report.html

## API Endpoints

- GET /health
- POST /predict
- POST /reload-model
- GET /monitoring
