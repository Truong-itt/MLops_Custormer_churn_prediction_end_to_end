import argparse
from pathlib import Path

import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        c.strip().replace(" ", "_").replace("-", "_").replace("/", "_") for c in df.columns
    ]
    return df


def normalize_target(df: pd.DataFrame, target_col: str = "Churn") -> pd.DataFrame:
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found")

    mapped = (
        df[target_col]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"1": 1, "yes": 1, "true": 1, "churn": 1, "0": 0, "no": 0, "false": 0, "active": 0})
    )
    if mapped.isna().any():
        unknown = sorted(df.loc[mapped.isna(), target_col].astype(str).unique().tolist())
        raise ValueError(f"Unknown target labels: {unknown}")
    df[target_col] = mapped.astype(int)
    return df


def transform_telco_schema(df: pd.DataFrame) -> pd.DataFrame:
    # Convert Telco dataset columns into the standardized feature schema used by training/API.
    out = pd.DataFrame()

    senior = (
        df["Senior Citizen"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"1": 1, "yes": 1, "true": 1, "0": 0, "no": 0, "false": 0})
        .fillna(0)
        .astype(int)
    )
    out["Age"] = senior.apply(lambda x: 65 if x == 1 else 35)
    out["Gender"] = df["Gender"].astype(str)
    out["Tenure"] = pd.to_numeric(df["Tenure Months"], errors="coerce").fillna(0).astype(int)
    out["Usage_Frequency"] = (
        (pd.to_numeric(df["Monthly Charges"], errors="coerce").fillna(0) / 5).round().clip(lower=0).astype(int)
    )
    out["Support_Calls"] = df["Tech Support"].astype(str).str.lower().map(
        {"no": 3, "yes": 0, "no internet service": 0}
    ).fillna(1).astype(int)
    out["Payment_Delay"] = df["Payment Method"].astype(str).str.lower().apply(
        lambda x: 8 if "electronic check" in x else 2
    )
    out["Subscription_Type"] = df["Internet Service"].astype(str)
    out["Contract_Length"] = df["Contract"].astype(str)
    out["Total_Spend"] = pd.to_numeric(df["Total Charges"], errors="coerce").fillna(0.0)
    out["Last_Interaction"] = out["Tenure"].apply(lambda x: int((30 - (x % 30)) if x > 0 else 30))
    out["Churn"] = pd.to_numeric(df["Churn Value"], errors="coerce").fillna(0).astype(int)

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess churn raw data")
    parser.add_argument("--input", required=True, help="Path to raw .xlsx")
    parser.add_argument("--output", required=True, help="Path to processed .csv")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_excel(input_path)
    # Handle either legacy schema or Telco schema from Newdata source.
    if {"Tenure Months", "Churn Value", "Monthly Charges"}.issubset(set(df.columns)):
        df = transform_telco_schema(df)
    else:
        df = normalize_columns(df)
        if "Churn" not in df.columns and "churn" in df.columns:
            df = df.rename(columns={"churn": "Churn"})
        df = normalize_target(df, target_col="Churn")

    df = df.drop_duplicates().reset_index(drop=True)
    df = df.fillna({
        "Gender": "Unknown",
        "Subscription_Type": "Unknown",
        "Contract_Length": "Unknown",
    })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Processed data saved to {output_path}")
    print(f"Rows={df.shape[0]}, Cols={df.shape[1]}")


if __name__ == "__main__":
    main()
