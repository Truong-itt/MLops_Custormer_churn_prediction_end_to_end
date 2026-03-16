import argparse
import json
import time
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient


def get_production_score(client: MlflowClient, model_name: str, metric_tag: str):
    try:
        prod = client.get_model_version_by_alias(model_name, "production")
        score = float(prod.tags.get(metric_tag, "-1"))
        return prod, score
    except Exception:
        return None, -1.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Register and rollout model in MLflow")
    parser.add_argument("--tracking-uri", default="http://localhost:5000")
    parser.add_argument("--model-name", default="churn_prediction_model")
    parser.add_argument("--run-info", required=True, help="Path to latest_run.json")
    parser.add_argument("--eval-gate", required=True, help="Path to eval gate json")
    parser.add_argument("--output", required=True, help="Path to deployment status json")
    args = parser.parse_args()

    mlflow.set_tracking_uri(args.tracking_uri)
    client = MlflowClient(tracking_uri=args.tracking_uri)

    run_info = json.loads(Path(args.run_info).read_text(encoding="utf-8"))
    eval_gate = json.loads(Path(args.eval_gate).read_text(encoding="utf-8"))

    if not eval_gate.get("passed", False):
        raise RuntimeError("Evaluation gate did not pass. Registration is blocked.")

    run_id = run_info["run_id"]
    metric_tag = run_info.get("metric_key", "val_roc_auc")
    candidate_score = float(run_info.get("metric_value", 0.0))

    try:
        client.get_registered_model(args.model_name)
    except Exception:
        client.create_registered_model(args.model_name)

    result = mlflow.register_model(model_uri=f"runs:/{run_id}/model", name=args.model_name)
    version = result.version

    for _ in range(30):
        mv = client.get_model_version(args.model_name, version)
        if mv.status == "READY":
            break
        time.sleep(1)

    client.set_model_version_tag(args.model_name, version, metric_tag, str(candidate_score))
    client.set_model_version_tag(args.model_name, version, "source_run_id", run_id)

    current_prod, prod_score = get_production_score(client, args.model_name, metric_tag)

    rollout = candidate_score > prod_score
    if rollout:
        client.set_registered_model_alias(args.model_name, "production", version)

    status = {
        "model_name": args.model_name,
        "candidate_version": version,
        "candidate_score": candidate_score,
        "production_score_before": prod_score,
        "production_version_before": getattr(current_prod, "version", None),
        "rolled_out": rollout,
        "production_version_after": version if rollout else getattr(current_prod, "version", None),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
