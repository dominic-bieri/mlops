from datetime import date

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.features.build import HORIZON, LABEL_COLUMN

TRAIN_END = date(2023, 12, 31)
TEST_START = date(2024, 1, 1)
VIX_STRESSED = 20

HAR_COLUMNS = ["rv_1d", "rv_5d", "rv_22d"]


def split(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    labelled = features.dropna(subset=[LABEL_COLUMN]).sort_values("date")
    # gap, so no training label reaches into the test period
    train = labelled[labelled["date"] <= TRAIN_END].iloc[:-HORIZON]
    test = labelled[labelled["date"] >= TEST_START]
    return train, test


def main() -> None:
    features = BigQueryClient().read_table("features")
    train, test = split(features)

    # HAR-RV (ADR 7): y = b0 + b1 * rv_1d + b2 * rv_5d + b3 * rv_22d, fitted on train only
    har = LinearRegression().fit(train[HAR_COLUMNS], train[LABEL_COLUMN])

    # scaled VIX (ADR 7): y = c * vix, c = mean label / mean vix
    # c < 1 removes the risk premium, the VIX is usually higher than the real volatility
    vix_factor = train[LABEL_COLUMN].mean() / train["vix"].mean()

    # absolute error |prediction - label|, the mean of it is the MAE
    label = test[LABEL_COLUMN]
    errors = pd.DataFrame(
        {
            "rv_20d": (test["rv_20d"] - label).abs(),
            "har_rv": (har.predict(test[HAR_COLUMNS]) - label).abs(),
            "vix_scaled": (vix_factor * test["vix"] - label).abs(),
        }
    )
    print(f"vix factor: {vix_factor:.2f}")
    print(f"mae since {TEST_START}:\n{errors.mean().round(2).to_string()}")

    errors["year"] = pd.to_datetime(test["date"]).dt.year
    errors["days"] = np.where(test["vix"] > VIX_STRESSED, "stressed", "calm")
    print(errors.groupby(["year", "days"]).mean().round(2).to_string())


if __name__ == "__main__":
    main()
