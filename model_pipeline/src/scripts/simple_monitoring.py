import argparse
import json
from pathlib import Path

import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report
from evidently.ui.dashboards import CounterAgg, DashboardPanelCounter, PanelValue, ReportFilter
from evidently.ui.workspace import Workspace


def load_inference_log(log_path: Path) -> pd.DataFrame:
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        payload = item.get("input", {})
        payload["prediction"] = item.get("prediction")
        payload["probability"] = item.get("probability")
        payload["timestamp"] = item.get("timestamp")
        rows.append(payload)
    return pd.DataFrame(rows)


def empty_summary(reason: str, output_json: Path, output_html: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_html.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "status": "no_data",
        "reason": reason,
        "dataset_drift": None,
        "share_of_drifted_columns": None,
        "reference_rows": 0,
        "current_rows": 0,
        "common_columns": [],
    }
    output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    output_html.write_text(
        "<html><body><h3>No drift report generated</h3><p>"
        + reason
        + "</p></body></html>",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


def push_to_evidently_workspace(report: Report, workspace_dir: Path, project_name: str) -> dict:
    workspace_dir.mkdir(parents=True, exist_ok=True)

    if (workspace_dir / "workspace.db").exists():
        ws = Workspace(str(workspace_dir))
    else:
        ws = Workspace.create(str(workspace_dir))

    projects = ws.search_project(project_name)
    if projects:
        project = projects[0]
    else:
        project = ws.create_project(project_name)

    deduped_panels = []
    seen_titles = set()
    for panel in project.dashboard.panels:
        if panel.title not in seen_titles:
            deduped_panels.append(panel)
            seen_titles.add(panel.title)
    project.dashboard.panels = deduped_panels

    existing_titles = {panel.title for panel in project.dashboard.panels}
    default_filter = ReportFilter(metadata_values={}, tag_values=[])

    dashboard_tab = None
    if project.dashboard.tabs:
        dashboard_tab = project.dashboard.tabs[0]
    else:
        dashboard_tab = project.dashboard.create_tab("Overview")

    if "Dataset Drift (Last)" not in existing_titles:
        project.dashboard.add_panel(
            DashboardPanelCounter(
                title="Dataset Drift (Last)",
                filter=default_filter,
                agg=CounterAgg.LAST,
                value=PanelValue(metric_id="DatasetDriftMetric", field_path="dataset_drift"),
            ),
            tab=dashboard_tab,
        )

    if (
        "Drifted Columns Share (Last)" not in existing_titles
        and "Share Drifted Columns (Last)" not in existing_titles
    ):
        project.dashboard.add_panel(
            DashboardPanelCounter(
                title="Drifted Columns Share (Last)",
                filter=default_filter,
                agg=CounterAgg.LAST,
                value=PanelValue(
                    metric_id="DatasetDriftMetric",
                    field_path="share_of_drifted_columns",
                ),
            ),
            tab=dashboard_tab,
        )

    if project.dashboard.tabs and project.dashboard.panels:
        first_tab = project.dashboard.tabs[0]
        project.dashboard.tab_id_to_panel_ids[str(first_tab.id)] = [
            panel.id for panel in project.dashboard.panels
        ]

    project.save()

    ws.add_report(project.id, report)
    return {
        "workspace_dir": str(workspace_dir),
        "project_id": str(project.id),
        "project_name": project_name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Evidently data drift report")
    parser.add_argument("--reference-data", required=True)
    parser.add_argument("--inference-log", required=True)
    parser.add_argument("--output-html", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--min-samples", type=int, default=2)
    parser.add_argument("--ui-workspace", default=None, help="Path to Evidently UI workspace")
    parser.add_argument("--ui-project", default="Churn Monitoring", help="Evidently UI project name")
    args = parser.parse_args()

    reference_path = Path(args.reference_data)
    inference_log_path = Path(args.inference_log)
    output_html = Path(args.output_html)
    output_json = Path(args.output_json)

    if not reference_path.exists():
        empty_summary("Reference dataset not found", output_json, output_html)
        return

    if not inference_log_path.exists():
        empty_summary("Inference log file not found", output_json, output_html)
        return

    reference_df = pd.read_csv(reference_path)
    current_df = load_inference_log(inference_log_path)

    if current_df.empty or len(current_df) < args.min_samples:
        empty_summary(
            f"Not enough inference samples. Need >= {args.min_samples}, got {len(current_df)}",
            output_json,
            output_html,
        )
        return

    common_cols = [
        c
        for c in current_df.columns
        if c in reference_df.columns and c not in {"Churn", "timestamp"}
    ]

    if not common_cols:
        empty_summary("No common columns between reference and current data", output_json, output_html)
        return

    ref = reference_df[common_cols].copy()
    cur = current_df[common_cols].copy()

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref, current_data=cur)

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(output_html))

    report_dict = report.as_dict()
    dataset_drift = None
    drift_share = None
    for metric in report_dict.get("metrics", []):
        if metric.get("metric") == "DatasetDriftMetric":
            result = metric.get("result", {})
            dataset_drift = result.get("dataset_drift")
            drift_share = result.get("share_of_drifted_columns")
            break

    summary = {
        "status": "ok",
        "dataset_drift": dataset_drift,
        "share_of_drifted_columns": drift_share,
        "reference_rows": int(len(ref)),
        "current_rows": int(len(cur)),
        "common_columns": common_cols,
        "report_html": str(output_html),
    }

    if args.ui_workspace:
        ui_meta = push_to_evidently_workspace(
            report=report,
            workspace_dir=Path(args.ui_workspace),
            project_name=args.ui_project,
        )
        summary.update(ui_meta)

    output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
