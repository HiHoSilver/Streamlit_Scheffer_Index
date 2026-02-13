# Each daily record is contained in a list of dicts:
# {
# "date": date,
# "avg_temp_f": tavg,
# "total_precip_in": prcp
# }

import pandas as pd
import numpy as np

def process_summaries(daily_results):
    df = pd.DataFrame(daily_results)

    # Convert date column
    df["date"] = pd.to_datetime(df["date"])

    # Build full date range for the year
    year = df["date"].dt.year.iloc[0]
    full_range = pd.date_range(f"{year}-01-01", f"{year}-12-31")

    # Reindex to include missing days
    df = (
        df.set_index("date")
          .reindex(full_range)
          .rename_axis("date")
          .reset_index()
    )

    # Data completeness
    missing_prcp = df["total_precip_in"].isna().sum()
    missing_temp = df["avg_temp_f"].isna().sum()
    data_completion_pct = (
        1 - ((missing_prcp + missing_temp) / (len(df) * 2))
    ) * 100

    # Before interpolation: keep a mask of original missing temps
    orig_missing_temp = df["avg_temp_f"].isna()

    # Interpolate temps
    df["avg_temp_f"] = df["avg_temp_f"].interpolate(limit_direction="both")


    # Monthly summaries
    df["month_num"] = df["date"].dt.month
    df["month"] = df["date"].dt.month_name()

    # Precip threshold: 1 = yes, 0 = no
    df["prcp_th"] = np.where(df["total_precip_in"] > 0.01, 1, 0)

    df_grouped = (
        df.groupby(["month_num", "month"])
          .agg({"avg_temp_f": "mean", "prcp_th": "sum"})
          .sort_values("month_num")
          .reset_index()
          .drop(columns="month_num")
    )

    return df_grouped, data_completion_pct

def calculate_index(df):
    # Apply T floor: if T < 35, use 0 instead of (T - 35)
    T_term = (df["avg_temp_f"] - 35).clip(lower=0)

    # D is already the number of days ≥ 0.01"
    D_term = df["prcp_th"] - 3

    # Monthly contributions
    monthly_values = (T_term * D_term) / 30

    # Summation over all months
    return monthly_values.sum()

