import argparse
import json
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET_COL = "Churn"
FEATURE_COLS = [
    "Age",
    "Gender",
    "Tenure",
    "Usage_Frequency",
    "Support_Calls",
    "Payment_Delay",
    "Subscription_Type",
    "Contract_Length",
    "Total_Spend",
    "Last_Interaction",
]


def build_preprocessor(df: pd.DataFrame) -> ColumnTransformer:
    numeric_cols = [c for c in FEATURE_COLS if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in FEATURE_COLS if c not in numeric_cols]

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_cols),
            ("cat", categorical_transformer, categorical_cols),
        ]
    )


def evaluate(y_true, y_pred, y_prob):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
    }


def train_and_log(
    model_name: str,
    model,
    preprocessor,
    x_train,
    x_val,
    y_train,
    y_val,
):
    pipe = Pipeline(steps=[("preprocess", preprocessor), ("model", model)])
    pipe.fit(x_train, y_train)
    y_pred = pipe.predict(x_val)
    y_prob = pipe.predict_proba(x_val)[:, 1]
    metrics = evaluate(y_val, y_pred, y_prob)

    mlflow.log_param("candidate_model", model_name)
    mlflow.log_metrics({f"val_{k}": v for k, v in metrics.items()})
    mlflow.sklearn.log_model(pipe, artifact_path="model", input_example=x_train.head(3))
    return pipe, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple churn training pipeline")
    parser.add_argument("--data", required=True, help="Feature dataset csv")
    parser.add_argument("--tracking-uri", default="http://localhost:5000")
    parser.add_argument("--experiment", default="churn_simple_experiment")
    parser.add_argument("--output-dir", default="model_pipeline/src/artifacts")
    args = parser.parse_args()

    data_path = Path(args.data)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(args.experiment)

    df = pd.read_csv(data_path)
    missing = [c for c in FEATURE_COLS + [TARGET_COL] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for training: {missing}")

    x = df[FEATURE_COLS].copy()
    y = df[TARGET_COL].astype(int)

    x_train, x_val, y_train, y_val = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )
    preprocessor = build_preprocessor(x_train)

    candidates = {
        "logistic_regression": LogisticRegression(max_iter=300, random_state=42),
        "random_forest": RandomForestClassifier(n_estimators=300, random_state=42),
    }

    best_name = None
    best_metrics = None
    best_run_id = None

    for candidate_name, model in candidates.items():
        with mlflow.start_run(run_name=f"train_{candidate_name}") as run:
            mlflow.log_params(
                {
                    "dataset": str(data_path),
                    "target": TARGET_COL,
                }
            )

            _, metrics = train_and_log(
                candidate_name,
                model,
                preprocessor,
                x_train,
                x_val,
                y_train,
                y_val,
            )

            if best_metrics is None or metrics["roc_auc"] > best_metrics["roc_auc"]:
                best_name = candidate_name
                best_metrics = metrics
                best_run_id = run.info.run_id

    if not best_run_id:
        raise RuntimeError("No successful training run produced")

    latest_run = {
        "run_id": best_run_id,
        "model_name": best_name,
        "metric_key": "val_roc_auc",
        "metric_value": best_metrics["roc_auc"],
    }
    (output_dir / "latest_run.json").write_text(json.dumps(latest_run, indent=2), encoding="utf-8")
    (output_dir / "latest_metrics.json").write_text(json.dumps(best_metrics, indent=2), encoding="utf-8")

    print(f"Best model run_id: {best_run_id}")
    print(f"Best model type: {best_name}")
    print(f"Best roc_auc: {best_metrics['roc_auc']:.4f}")


if __name__ == "__main__":
    main()
