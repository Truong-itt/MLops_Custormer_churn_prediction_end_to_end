from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXTERNAL_LOG_DIR = Path("/opt/project/infra/docker/student/logs")
TASK_EVENTS_FILE = EXTERNAL_LOG_DIR / "task_events.jsonl"
RUN_SUMMARY_DIR = EXTERNAL_LOG_DIR / "run_summaries"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(file_path: Path, payload: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _task_context(context: dict[str, Any]) -> dict[str, Any]:
    ti = context.get("ti")
    dag_run = context.get("dag_run")
    logical_date = context.get("logical_date")
    return {
        "timestamp": _utc_now_iso(),
        "dag_id": getattr(ti, "dag_id", None),
        "task_id": getattr(ti, "task_id", None),
        "run_id": getattr(dag_run, "run_id", None),
        "try_number": getattr(ti, "try_number", None),
        "state": getattr(ti, "state", None),
        "logical_date": logical_date.isoformat() if logical_date else None,
    }


def log_task_event(
    *,
    event_type: str,
    context: dict[str, Any],
    message: str | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = _task_context(context)
    payload["event_type"] = event_type
    if message:
        payload["message"] = message
    if error:
        payload["error"] = error
    if extra:
        payload["extra"] = extra
    _append_jsonl(TASK_EVENTS_FILE, payload)


def on_task_success(context: dict[str, Any]) -> None:
    log_task_event(event_type="task_success", context=context, message="Task completed successfully")


def on_task_failure(context: dict[str, Any]) -> None:
    error = context.get("exception")
    log_task_event(
        event_type="task_failed",
        context=context,
        message="Task failed",
        error=str(error) if error else "Unknown error",
    )


def on_task_skipped(context: dict[str, Any]) -> None:
    log_task_event(event_type="task_skipped", context=context, message="Task was skipped")


def write_run_summary(**context: Any) -> None:
    dag_run = context["dag_run"]
    ti = context["ti"]
    current_task_id = ti.task_id
    skip_reason = ti.xcom_pull(task_ids="check_new_data", key="skip_reason")

    task_summaries: list[dict[str, Any]] = []
    for instance in sorted(dag_run.get_task_instances(), key=lambda x: x.task_id):
        item = {
            "task_id": instance.task_id,
            "state": instance.state,
            "try_number": instance.try_number,
            "start_date": instance.start_date.isoformat() if instance.start_date else None,
            "end_date": instance.end_date.isoformat() if instance.end_date else None,
            "duration_seconds": instance.duration,
        }
        if instance.task_id == current_task_id:
            item["state"] = "success"
            item["end_date"] = _utc_now_iso()
            if item["duration_seconds"] is None:
                item["duration_seconds"] = 0.0
        if instance.state == "skipped" and skip_reason:
            item["reason"] = skip_reason
        task_summaries.append(item)

    effective_tasks = [t for t in task_summaries if t["task_id"] != current_task_id]
    total = len(effective_tasks)
    skipped = sum(1 for t in effective_tasks if t["state"] == "skipped")
    failed = sum(1 for t in effective_tasks if t["state"] == "failed")
    upstream_failed = sum(1 for t in effective_tasks if t["state"] == "upstream_failed")
    success = sum(1 for t in effective_tasks if t["state"] == "success")

    if failed > 0 or upstream_failed > 0:
        overall_state = "failed"
    elif success + skipped == total:
        overall_state = "success"
    else:
        overall_state = "running"

    summary = {
        "timestamp": _utc_now_iso(),
        "dag_id": dag_run.dag_id,
        "run_id": dag_run.run_id,
        "overall_state": overall_state,
        "skip_reason": skip_reason,
        "counts": {
            "total_tasks": total,
            "success": success,
            "failed": failed,
            "upstream_failed": upstream_failed,
            "skipped": skipped,
        },
        "tasks": task_summaries,
    }

    safe_run_id = dag_run.run_id.replace(":", "_").replace("/", "_")
    summary_path = RUN_SUMMARY_DIR / f"{dag_run.dag_id}__{safe_run_id}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    log_task_event(
        event_type="dag_run_summary",
        context=context,
        message="Wrote DAG run summary",
        extra={"summary_path": str(summary_path)},
    )