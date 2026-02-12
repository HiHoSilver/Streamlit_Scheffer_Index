# Each daily record is contained in a list of dicts:
# {
# "date": date,
# "avg_temp_f": tavg,
# "total_precip_in": prcp
# }

import pandas as pd
import numpy as np

def process_data(daily_results):
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

    # Monthly summaries
    df["month_num"] = df["date"].dt.month
    df["month"] = df["date"].dt.month_name()

    # Precip threshold: 1 = yes, 0 = no
    df["prcp_th"] = np.where(df["total_precip_in"] > 0.1, 1, 0)

    df_grouped = (
        df.groupby(["month_num", "month"])
          .agg({"avg_temp_f": "mean", "prcp_th": "sum"})
          .sort_values("month_num")
          .reset_index()
          .drop(columns="month_num")
    )

    return df_grouped, data_completion_pct
