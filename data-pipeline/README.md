# Data Pipeline (Simplified)

This folder contains the active file-based batch data pipeline.

## Active Input

- data/Newdata/Telco_customer_churn.xlsx

## Active Outputs

- data/raw/telco_customer_churn.xlsx
- data/processed/churn_processed.csv
- data/processed/churn_features.csv

## Active Scripts

- scripts/simple_ingest.py
- scripts/simple_validate.py
- scripts/simple_preprocess.py
- scripts/simple_build_features.py

## How It Is Used

These scripts are called by Airflow DAG churn_batch_pipeline from:
- infra/docker/student/dags/churn_batch_pipeline.py

## Notes

This cleaned project no longer uses DVC, Feast, Redis, or Spark in the active path.
