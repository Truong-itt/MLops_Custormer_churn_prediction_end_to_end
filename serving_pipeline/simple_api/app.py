import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

import mlflow
import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "churn_prediction_model")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "production")
INFERENCE_LOG_PATH = Path(os.getenv("INFERENCE_LOG_PATH", "/app/logs/inference_log.jsonl"))
DRIFT_SUMMARY_PATH = Path(os.getenv("DRIFT_SUMMARY_PATH", "/app/reports/drift_summary.json"))

_model_lock = Lock()
_model = None
_model_uri = None


class PredictRequest(BaseModel):
    Age: int = Field(..., ge=18, le=100)
    Gender: str
    Tenure: int = Field(..., ge=0)
    Usage_Frequency: int = Field(..., ge=0)
    Support_Calls: int = Field(..., ge=0)
    Payment_Delay: int = Field(..., ge=0)
    Subscription_Type: str
    Contract_Length: str
    Total_Spend: float = Field(..., ge=0)
    Last_Interaction: int = Field(..., ge=0)


class PredictResponse(BaseModel):
    churn_prediction: int
    churn_probability: float
    model_uri: str


app = FastAPI(title="Simple Churn Serving API", version="1.0.0")


def _resolve_model_uri() -> str:
    return f"models:/{MODEL_NAME}@{MODEL_ALIAS}"


def _append_inference_log(payload: dict) -> None:
    INFERENCE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INFERENCE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _inference_stats() -> dict:
    if not INFERENCE_LOG_PATH.exists():
        return {"count": 0, "last_timestamp": "N/A"}

    lines = INFERENCE_LOG_PATH.read_text(encoding="utf-8").splitlines()
    if not lines:
        return {"count": 0, "last_timestamp": "N/A"}

    last_ts = "N/A"
    try:
        last_ts = json.loads(lines[-1]).get("timestamp", "N/A")
    except Exception:
        pass

    return {"count": len(lines), "last_timestamp": last_ts}


def _drift_summary() -> dict:
    if not DRIFT_SUMMARY_PATH.exists():
        return {
            "status": "no_report",
            "dataset_drift": None,
            "share_of_drifted_columns": None,
        }
    try:
        return json.loads(DRIFT_SUMMARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "status": "invalid_report",
            "dataset_drift": None,
            "share_of_drifted_columns": None,
        }


def load_model(force: bool = False) -> str:
    global _model, _model_uri
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    with _model_lock:
        target_uri = _resolve_model_uri()
        if (not force) and (_model is not None) and (_model_uri == target_uri):
            return _model_uri

        _model = mlflow.pyfunc.load_model(target_uri)
        _model_uri = target_uri
        return _model_uri


@app.on_event("startup")
def startup_event() -> None:
    try:
        load_model(force=True)
    except Exception:
        # API still starts even when no production model exists yet.
        pass


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    stats = _inference_stats()
    drift = _drift_summary()
    model_status = "Loaded" if _model is not None else "Not loaded"
    model_uri = _model_uri or "N/A"
    current_time = datetime.utcnow().isoformat()

    return f"""
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Churn System Dashboard</title>
    <style>
        :root {{
            --bg: #f4f4f4;
            --panel: #ffffff;
            --text: #111111;
            --line: #1f1f1f;
            --muted: #5a5a5a;
        }}
        * {{ box-sizing: border-box; border-radius: 0 !important; }}
        body {{
            margin: 0;
            font-family: "Segoe UI", Tahoma, sans-serif;
            background: var(--bg);
            color: var(--text);
        }}
        .wrap {{
            max-width: 980px;
            margin: 24px auto;
            padding: 0 16px;
        }}
        h1 {{ margin: 0 0 14px; font-size: 26px; font-weight: 700; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
        }}
        .card {{
            background: var(--panel);
            border: 1px solid var(--line);
            padding: 14px;
        }}
        .label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
        .value {{ margin-top: 6px; font-size: 14px; font-weight: 600; word-break: break-word; }}
        .section {{
            margin-top: 12px;
            background: var(--panel);
            border: 1px solid var(--line);
            padding: 14px;
        }}
        .section h2 {{ margin: 0 0 10px; font-size: 18px; }}
        ul {{ margin: 0; padding-left: 18px; }}
        li {{ margin: 6px 0; }}
        code {{
            background: #ececec;
            border: 1px solid #c5c5c5;
            padding: 1px 5px;
            font-family: Consolas, monospace;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class=\"wrap\">
        <h1>Customer Churn Prediction System</h1>
        <div class=\"grid\">
            <div class=\"card\">
                <div class=\"label\">Model Status</div>
                <div class=\"value\">{model_status}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">Model URI</div>
                <div class=\"value\">{model_uri}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">MLflow Tracking</div>
                <div class=\"value\">{MLFLOW_TRACKING_URI}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">Total Inference Logs</div>
                <div class=\"value\">{stats['count']}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">Last Inference Time</div>
                <div class=\"value\">{stats['last_timestamp']}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">Current UTC Time</div>
                <div class=\"value\">{current_time}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">Drift Report Status</div>
                <div class=\"value\">{drift.get('status', 'N/A')}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">Dataset Drift</div>
                <div class=\"value\">{drift.get('dataset_drift', 'N/A')}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">Drifted Columns Share</div>
                <div class=\"value\">{drift.get('share_of_drifted_columns', 'N/A')}</div>
            </div>
            <div class=\"card\">
                <div class=\"label\">Evidently UI</div>
                <div class=\"value\"><a href=\"http://localhost:8001\" target=\"_blank\">http://localhost:8001</a></div>
            </div>
        </div>

        <div class=\"section\">
            <h2>Available Endpoints</h2>
            <ul>
                <li><code>GET /health</code> : API health status</li>
                <li><code>POST /predict</code> : churn prediction</li>
                <li><code>POST /reload-model</code> : reload production model</li>
                <li><code>GET /monitoring</code> : Evidently summary JSON</li>
                <li><code>GET http://localhost:8001</code> : Evidently UI dashboard</li>
                <li><code>GET /docs</code> : Swagger UI</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""


@app.get("/monitoring")
def monitoring() -> dict:
    return _drift_summary()


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "model_loaded": _model is not None,
        "model_uri": _model_uri,
        "tracking_uri": MLFLOW_TRACKING_URI,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/reload-model")
def reload_model() -> dict:
    try:
        uri = load_model(force=True)
        return {"reloaded": True, "model_uri": uri}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reload failed: {exc}")


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    try:
        if _model is None:
            load_model(force=True)

        data = pd.DataFrame([payload.model_dump()])
        pred = int(_model.predict(data)[0])

        prob = 0.5
        model_impl = getattr(_model, "_model_impl", None)
        if model_impl is not None and hasattr(model_impl, "predict_proba"):
            prob = float(model_impl.predict_proba(data)[0][1])

        log_item = {
            "timestamp": datetime.utcnow().isoformat(),
            "input": payload.model_dump(),
            "prediction": pred,
            "probability": prob,
            "model_uri": _model_uri,
        }
        _append_inference_log(log_item)

        return PredictResponse(
            churn_prediction=pred,
            churn_probability=prob,
            model_uri=_model_uri or "unknown",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")
