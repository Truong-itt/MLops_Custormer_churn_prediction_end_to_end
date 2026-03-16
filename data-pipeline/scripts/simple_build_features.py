import argparse
from pathlib import Path

import pandas as pd


FEATURE_COLUMNS = [
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
    "Churn",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build simple feature dataset")
    parser.add_argument("--input", required=True, help="Path to processed csv")
    parser.add_argument("--output", required=True, help="Path to feature csv")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_csv(input_path)
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")

    feature_df = df[FEATURE_COLUMNS].copy()
    feature_df = feature_df.dropna(subset=["Churn"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_csv(output_path, index=False)
    print(f"Feature dataset saved to {output_path}")
    print(f"Rows={feature_df.shape[0]}, Cols={feature_df.shape[1]}")


if __name__ == "__main__":
    main()
