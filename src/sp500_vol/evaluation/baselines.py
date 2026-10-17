from datetime import date

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.features.build import HORIZON, LABEL_COLUMN

# windows end at the newest labelled day and move forward with it
TEST_MONTHS = 12
VAL_MONTHS = 24
VIX_STRESSED = 20

HAR_COLUMNS = ["rv_1d", "rv_5d", "rv_22d"]


def months_before(day: date, months: int) -> date:
    timestamp = pd.Timestamp(day) - pd.DateOffset(months=months)
    return timestamp.date()


def get_cutoff(features: pd.DataFrame) -> date:
    labelled = features.dropna(subset=[LABEL_COLUMN])
    return labelled["date"].max()


def split(features: pd.DataFrame, cutoff: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labelled = features.dropna(subset=[LABEL_COLUMN]).sort_values("date")
    labelled = labelled[labelled["date"] <= cutoff]

    test_start = months_before(cutoff, TEST_MONTHS)
    val_start = months_before(test_start, VAL_MONTHS)

    # gap of HORIZON rows, so no label reaches into the next window
    train = labelled[labelled["date"] <= val_start].iloc[:-HORIZON]
    in_val = (labelled["date"] > val_start) & (labelled["date"] <= test_start)
    val = labelled[in_val].iloc[:-HORIZON]
    test = labelled[labelled["date"] > test_start]
    return train, val, test


def get_errors(df: pd.DataFrame, har: LinearRegression, vix_factor: float) -> pd.DataFrame:
    label = df[LABEL_COLUMN]
    return pd.DataFrame(
        {
            "rv_20d": (df["rv_20d"] - label).abs(),
            "har_rv": (har.predict(df[HAR_COLUMNS]) - label).abs(),
            "vix_scaled": (vix_factor * df["vix"] - label).abs(),
        }
    )


def main() -> None:
    features = BigQueryClient().read_table("features")
    cutoff = get_cutoff(features)
    train, val, test = split(features, cutoff)
    print(f"cutoff: {cutoff}")
    print(f"train: {train['date'].min()} to {train['date'].max()}")
    print(f"val:   {val['date'].min()} to {val['date'].max()}")
    print(f"test:  {test['date'].min()} to {test['date'].max()}")

    har = LinearRegression().fit(train[HAR_COLUMNS], train[LABEL_COLUMN])
    vix_factor = train[LABEL_COLUMN].mean() / train["vix"].mean()

    print(f"vix factor: {vix_factor:.2f}")

    test_errors = get_errors(test, har, vix_factor)
    print(f"mae on test:\n{test_errors.mean().round(2).to_string()}")

    # baselines are fitted on train only, so val is unseen too and adds more years
    unseen = pd.concat([val, test])
    errors = get_errors(unseen, har, vix_factor)
    errors["year"] = pd.to_datetime(unseen["date"]).dt.year
    errors["days"] = np.where(unseen["vix"] > VIX_STRESSED, "stressed", "calm")
    print(errors.groupby(["year", "days"]).mean().round(2).to_string())


if __name__ == "__main__":
    main()
