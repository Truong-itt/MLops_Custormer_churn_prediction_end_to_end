import argparse
from pathlib import Path

import pandas as pd


LEGACY_REQUIRED_COLUMNS = {
    "Age",
    "Gender",
    "Tenure",
    "Usage Frequency",
    "Support Calls",
    "Payment Delay",
    "Subscription Type",
    "Contract Length",
    "Total Spend",
    "Last Interaction",
    "Churn",
}

TELCO_REQUIRED_COLUMNS = {
    "Gender",
    "Senior Citizen",
    "Tenure Months",
    "Contract",
    "Internet Service",
    "Monthly Charges",
    "Total Charges",
    "Churn Value",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate raw churn Excel schema")
    parser.add_argument("--input", required=True, help="Path to raw .xlsx")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")

    df = pd.read_excel(input_path)
    cols = set(df.columns)
    legacy_ok = LEGACY_REQUIRED_COLUMNS.issubset(cols)
    telco_ok = TELCO_REQUIRED_COLUMNS.issubset(cols)
    if not (legacy_ok or telco_ok):
        missing_legacy = sorted(LEGACY_REQUIRED_COLUMNS.difference(cols))
        missing_telco = sorted(TELCO_REQUIRED_COLUMNS.difference(cols))
        raise ValueError(
            "Input schema not recognized. "
            f"Missing legacy columns: {missing_legacy}. "
            f"Missing telco columns: {missing_telco}."
        )

    if df.shape[0] < 100:
        raise ValueError("Dataset too small for training. Need at least 100 rows.")

    quality_cols = list(TELCO_REQUIRED_COLUMNS) if telco_ok else list(LEGACY_REQUIRED_COLUMNS)
    null_ratio = df[quality_cols].isnull().mean().max()
    if null_ratio > 0.4:
        raise ValueError(f"Data quality issue: max null ratio is {null_ratio:.2f}")

    print(f"Validation passed. rows={df.shape[0]} cols={df.shape[1]}")


if __name__ == "__main__":
    main()
