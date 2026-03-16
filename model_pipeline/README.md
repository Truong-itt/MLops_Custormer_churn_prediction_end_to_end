# Model Pipeline (Simplified)

This folder contains the simplified training and monitoring scripts used by the current project stack.

## Active Structure

```text
model_pipeline/
  README.md
  src/
    artifacts/
    scripts/
      simple_train.py
      simple_evaluate.py
      simple_register_rollout.py
      simple_monitoring.py
```

## Script Roles

- simple_train.py
  - train baseline models
  - log runs/metrics/model to MLflow
  - save best run info to artifacts

- simple_evaluate.py
  - apply threshold gate (roc_auc, f1)
  - write eval result to artifacts

- simple_register_rollout.py
  - register model version
  - compare with current production score
  - update production alias when better

- simple_monitoring.py
  - run Evidently drift report
  - write drift summary JSON + HTML
  - push report to Evidently UI workspace/project

## Artifacts

Generated under src/artifacts:
- latest_run.json
- latest_metrics.json
- eval_gate.json
- deploy_status.json

## Notes

This README intentionally reflects only the active simplified pipeline.
Legacy XGBoost/MinIO/Feast/Kafka-related instructions are deprecated in this cleaned project.
   # Run A/B tests
   # Validate performance
   
   # Promote when ready
   ./promote_model.sh
   ```

3. **Production Deployment**
   ```bash
   # Always compare against current champion
   python src/scripts/eval.py \
       --model-uri "models:/xgboost_churn_model@staging" \
       --compare-baseline "models:/xgboost_churn_model@champion"
   
   # If improvement confirmed, promote
   ./promote_model.sh
   ```

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                     MLflow UI (Port 5000)                │
│                   Experiment Tracking & Registry         │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │    MinIO     │ │Training/Eval │
│   Metadata   │ │  Artifacts   │ │   Scripts    │
│   Storage    │ │  (S3-like)   │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Data Flow

```
Input Data → Preprocessing → Training → Evaluation → Registration → Production
    ↓            ↓              ↓           ↓            ↓             ↓
  Raw CSV    Cleaned Data   XGBoost    Metrics     Model URI    Deployed Model
                                       SHAP         Version
```

### Module Architecture

```
mlflow_utils/
├── experiment_tracker.py   → Handles run lifecycle, logging
└── model_registry.py       → Model versioning, aliases

model/
├── xgboost_trainer.py     → Training pipeline, feature engineering
└── evaluator.py          → Evaluation metrics, SHAP

scripts/
├── train.py              → CLI for training
├── eval.py               → CLI for evaluation
└── register_model.py     → CLI for registry operations
```