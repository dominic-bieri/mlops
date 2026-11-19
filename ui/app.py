import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")
# name in the API: label, color; Model and Actual stand out, baselines muted
LINES = {
    "model": ("Model", "#2563eb"),
    "har_rv": ("HAR-RV", "#d4b483"),
    "rv_20d": ("20-day vol", "#b8a9d9"),
    "vix_scaled": ("VIX scaled", "#e0a3a3"),
    "actual": ("Actual", "#10b981"),
}
# in trading days
PRESETS = {"3 months": 63, "1 year": 252, "All": None}


# the data changes once a day
@st.cache_data(ttl=600)
def get(path: str) -> dict | list:
    # long timeout, the API may need a cold start
    response = requests.get(f"{API_URL}{path}", timeout=60)
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="S&P 500 Volatility Forecast")
st.title("S&P 500 volatility, next 5 trading days")

with st.spinner("Loading, the service may need a few seconds to wake up."):
    model = get("/model")
    rows = pd.DataFrame(
        get("/predictions"),
        columns=[
            "date",
            "model",
            "har_rv",
            "rv_20d",
            "vix_scaled",
            "vix",
            "actual",
            "backfill",
            "model_version",
            "predicted_at",
        ],
    )
    forecast = rows.iloc[-1]


def label(name: str) -> str:
    return LINES[name][0]


st.metric("Forecast", f"{forecast['model']:.1f} %")
# 2026-11-14T15:01:30Z -> 2026-11-14 15:01
predicted_at = forecast["predicted_at"][:16].replace("T", " ")
st.caption(
    f"Model version {model['model_version']} (trained until {model['train_end']}) · "
    f"features as of {forecast['date']} · forecast made {predicted_at} UTC · "
    f"VIX {forecast['vix']:.1f} · "
    f"drift: {', '.join(model['drifted']) or 'none'}"
)
if model["stale"]:
    st.warning("Data is older than expected, the feature pipeline may have failed.")

chart = rows.set_index(pd.to_datetime(rows["date"]))
preset = st.segmented_control("Range", list(PRESETS), default="3 months")
if days := PRESETS.get(preset):
    chart = chart.tail(days)
lines = st.pills(
    "Lines", list(LINES), selection_mode="multi", default=["model", "actual"], format_func=label
)
if chart.empty:
    st.info("No forecasts yet, the first comes with the next feature run.")
elif lines:
    st.line_chart(
        chart[lines].rename(columns=label),
        y_label="Volatility (%)",
        color=[LINES[line][1] for line in lines],
    )
else:
    st.info("Select at least one line.")

is_live = ~rows["backfill"].astype(bool)
live = rows[is_live & (rows["model_version"] == model["model_version"])]
mae = pd.DataFrame(
    [model["test_mae"], model["live_mae"]],
    index=[
        "Test (12 months after training)",
        f"Live ({model['live_days']} of {len(live)} forecasts evaluated)",
    ],
)
forecasts = [name for name in LINES if name != "actual"]
st.table(mae[forecasts].rename(columns=label).style.format("{:.2f}", na_rep="–"))

first_live = rows.loc[is_live, "date"].min()
st.caption(
    "Annualized volatility of SPY in percent, forecast for the next 5 trading days, the actual "
    f"value is known 5 trading days later. Live since {first_live}, before: test period, forecast "
    "later. Not a trading signal."
)
