import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

import mlflow
import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "churn_prediction_model")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "production")
INFERENCE_LOG_PATH = Path(os.getenv("INFERENCE_LOG_PATH", "/app/logs/inference_log.jsonl"))

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
