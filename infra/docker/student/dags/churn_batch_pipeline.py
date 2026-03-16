from __future__ import annotations

import hashlib
import json
from pathlib import Path
from datetime import datetime

import requests
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, ShortCircuitOperator


PROJECT_ROOT = Path("/opt/project")
SOURCE_XLSX = PROJECT_ROOT / "data-pipeline/data/Newdata/Telco_customer_churn.xlsx"
RAW_XLSX = PROJECT_ROOT / "data-pipeline/data/raw/telco_customer_churn.xlsx"
INGEST_STATE = PROJECT_ROOT / "data-pipeline/data/raw/_ingest_state.json"

PROCESSED_CSV = PROJECT_ROOT / "data-pipeline/data/processed/churn_processed.csv"
FEATURE_CSV = PROJECT_ROOT / "data-pipeline/data/processed/churn_features.csv"

ARTIFACTS_DIR = PROJECT_ROOT / "model_pipeline/src/artifacts"
LATEST_RUN = ARTIFACTS_DIR / "latest_run.json"
LATEST_METRICS = ARTIFACTS_DIR / "latest_metrics.json"
EVAL_GATE = ARTIFACTS_DIR / "eval_gate.json"
DEPLOY_STATUS = ARTIFACTS_DIR / "deploy_status.json"


def _md5(file_path: Path) -> str:
    h = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def check_new_data(**context) -> bool:
    dag_run = context.get("dag_run")
    if dag_run and dag_run.conf and dag_run.conf.get("force_run", False):
        print("force_run=true detected. Execute full pipeline.")
        return True

    if not SOURCE_XLSX.exists():
        raise FileNotFoundError(f"Missing source file: {SOURCE_XLSX}")

    current = _md5(SOURCE_XLSX)
    if not INGEST_STATE.exists():
        return True

    state = json.loads(INGEST_STATE.read_text(encoding="utf-8"))
    previous = state.get("md5")
    return current != previous


def deploy_model() -> None:
    if not DEPLOY_STATUS.exists():
        raise FileNotFoundError(f"Missing deployment status file: {DEPLOY_STATUS}")

    status = json.loads(DEPLOY_STATUS.read_text(encoding="utf-8"))
    if not status.get("rolled_out", False):
        print("No rollout performed. Skip API reload.")
        return

    response = requests.post("http://fastapi:8000/reload-model", timeout=20)
    response.raise_for_status()
    print(f"Reload response: {response.json()}")


def notify_status() -> None:
    if not DEPLOY_STATUS.exists():
        raise FileNotFoundError(f"Missing deployment status file: {DEPLOY_STATUS}")
    status = json.loads(DEPLOY_STATUS.read_text(encoding="utf-8"))
    print("Pipeline finished with deployment summary:")
    print(json.dumps(status, indent=2))


with DAG(
    dag_id="churn_batch_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule="0 */6 * * *",
    catchup=False,
    tags=["churn", "student", "batch"],
) as dag:
    check_new_data_task = ShortCircuitOperator(
        task_id="check_new_data",
        python_callable=check_new_data,
    )

    ingest_raw_data = BashOperator(
        task_id="ingest_raw_data",
        bash_command=(
            "python /opt/project/data-pipeline/scripts/simple_ingest.py "
            "--source /opt/project/data-pipeline/data/Newdata/Telco_customer_churn.xlsx "
            "--dest /opt/project/data-pipeline/data/raw/telco_customer_churn.xlsx "
            "--state-file /opt/project/data-pipeline/data/raw/_ingest_state.json"
        ),
    )

    validate_data = BashOperator(
        task_id="validate_data",
        bash_command=(
            "python /opt/project/data-pipeline/scripts/simple_validate.py "
            "--input /opt/project/data-pipeline/data/raw/telco_customer_churn.xlsx"
        ),
    )

    preprocess_data = BashOperator(
        task_id="preprocess_data",
        bash_command=(
            "python /opt/project/data-pipeline/scripts/simple_preprocess.py "
            "--input /opt/project/data-pipeline/data/raw/telco_customer_churn.xlsx "
            "--output /opt/project/data-pipeline/data/processed/churn_processed.csv"
        ),
    )

    build_features = BashOperator(
        task_id="build_features",
        bash_command=(
            "python /opt/project/data-pipeline/scripts/simple_build_features.py "
            "--input /opt/project/data-pipeline/data/processed/churn_processed.csv "
            "--output /opt/project/data-pipeline/data/processed/churn_features.csv"
        ),
    )

    train_model = BashOperator(
        task_id="train_model",
        bash_command=(
            "python /opt/project/model_pipeline/src/scripts/simple_train.py "
            "--data /opt/project/data-pipeline/data/processed/churn_features.csv "
            "--tracking-uri http://mlflow:5000 "
            "--experiment churn_simple_experiment_v2 "
            "--output-dir /opt/project/model_pipeline/src/artifacts"
        ),
    )

    evaluate_model = BashOperator(
        task_id="evaluate_model",
        bash_command=(
            "python /opt/project/model_pipeline/src/scripts/simple_evaluate.py "
            "--metrics /opt/project/model_pipeline/src/artifacts/latest_metrics.json "
            "--min-roc-auc 0.70 "
            "--min-f1 0.59 "
            "--output /opt/project/model_pipeline/src/artifacts/eval_gate.json"
        ),
    )

    register_model = BashOperator(
        task_id="register_model",
        bash_command=(
            "python /opt/project/model_pipeline/src/scripts/simple_register_rollout.py "
            "--tracking-uri http://mlflow:5000 "
            "--model-name churn_prediction_model "
            "--run-info /opt/project/model_pipeline/src/artifacts/latest_run.json "
            "--eval-gate /opt/project/model_pipeline/src/artifacts/eval_gate.json "
            "--output /opt/project/model_pipeline/src/artifacts/deploy_status.json"
        ),
    )

    deploy_model_task = PythonOperator(
        task_id="deploy_model",
        python_callable=deploy_model,
    )

    monitor_drift = BashOperator(
        task_id="monitor_drift",
        bash_command=(
            "python /opt/project/model_pipeline/src/scripts/simple_monitoring.py "
            "--reference-data /opt/project/data-pipeline/data/processed/churn_features.csv "
            "--inference-log /opt/project/serving_pipeline/simple_api/logs/inference_log.jsonl "
            "--output-html /opt/project/serving_pipeline/simple_api/reports/drift_report.html "
            "--output-json /opt/project/serving_pipeline/simple_api/reports/drift_summary.json "
            "--ui-workspace /opt/project/serving_pipeline/simple_api/evidently_workspace "
            "--ui-project Churn_Monitoring "
            "--min-samples 2"
        ),
    )

    notify_status_task = PythonOperator(
        task_id="notify_status",
        python_callable=notify_status,
    )

    (
        check_new_data_task
        >> ingest_raw_data
        >> validate_data
        >> preprocess_data
        >> build_features
        >> train_model
        >> evaluate_model
        >> register_model
        >> deploy_model_task
        >> monitor_drift
        >> notify_status_task
    )
