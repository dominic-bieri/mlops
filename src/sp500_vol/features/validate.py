from datetime import date, timedelta

import exchange_calendars
import pandas as pd

from sp500_vol.common.log import github_warning

PRICE_COLUMNS = ["open", "high", "low", "close"]
MIN_FEATURE_ROWS = 5000
MAX_FEATURE_AGE_DAYS = 10
MAX_TRADING_DAYS_BEHIND = 1


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


def validate_features(df: pd.DataFrame, today: date) -> None:
    if len(df) < MIN_FEATURE_ROWS:
        raise ValueError(f"features: only {len(df)} rows, expected at least {MIN_FEATURE_ROWS}")

    newest = df["date"].max()
    age = (pd.Timestamp(today) - pd.Timestamp(newest)).days
    if age > MAX_FEATURE_AGE_DAYS:
        raise ValueError(f"features: newest row {newest} is {age} days old")


def get_trading_days_behind(newest: date, today: date) -> int:
    calendar = exchange_calendars.get_calendar("XNYS")
    last_trading_day = calendar.date_to_session(today - timedelta(days=1), "previous").date()
    if newest >= last_trading_day:
        return 0
    return calendar.sessions_distance(newest, last_trading_day) - 1


def check_freshness(newest: date, today: date) -> None:
    behind = get_trading_days_behind(newest, today)
    if behind == 0:
        return

    message = f"newest day {newest}, {behind} trading day(s) missing, no VIX or SPY yet"
    if behind > MAX_TRADING_DAYS_BEHIND:
        raise ValueError(f"features: {message}")
    github_warning("Features: not fresh", message)
