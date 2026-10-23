import pandas as pd

PRICE_COLUMNS = ["open", "high", "low", "close"]


def check(df: pd.DataFrame, bad: pd.Series, source: str, reason: str) -> None:
    if not bad.any():
        return

    dates = ", ".join(str(day) for day in df.loc[bad, "date"].head(5))
    raise ValueError(f"{source}: {reason} on {dates}")


def validate_spy(df: pd.DataFrame) -> None:
    columns = PRICE_COLUMNS + ["div_cash"]
    check(df, df[columns].isna().any(axis=1), "SPY", "missing value")
    check(df, (df[PRICE_COLUMNS] <= 0).any(axis=1), "SPY", "price not above 0")
    check(df, df["div_cash"] < 0, "SPY", "negative dividend")

    open_close = df[["open", "close"]]
    inside = (df["low"] <= open_close.min(axis=1)) & (open_close.max(axis=1) <= df["high"])
    check(df, ~inside, "SPY", "open or close outside low and high")
    check(df, df["date"].duplicated(), "SPY", "duplicate date")


def validate_vix(df: pd.DataFrame) -> None:
    check(df, df["close"].isna(), "VIX", "missing value")
    check(df, df["close"] <= 0, "VIX", "value not above 0")
    check(df, df["date"].duplicated(), "VIX", "duplicate date")
