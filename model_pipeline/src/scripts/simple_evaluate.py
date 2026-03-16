import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate gate for churn model")
    parser.add_argument("--metrics", required=True, help="Path to metrics json")
    parser.add_argument("--min-roc-auc", type=float, default=0.70)
    parser.add_argument("--min-f1", type=float, default=0.60)
    parser.add_argument("--output", required=True, help="Path to evaluation summary json")
    args = parser.parse_args()

    metrics_path = Path(args.metrics)
    output_path = Path(args.output)

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    roc_auc = float(metrics.get("roc_auc", 0.0))
    f1 = float(metrics.get("f1", 0.0))

    passed = (roc_auc >= args.min_roc_auc) and (f1 >= args.min_f1)
    summary = {
        "passed": passed,
        "roc_auc": roc_auc,
        "f1": f1,
        "min_roc_auc": args.min_roc_auc,
        "min_f1": args.min_f1,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if not passed:
        raise SystemExit("Evaluation gate failed. Stop rollout.")


if __name__ == "__main__":
    main()
