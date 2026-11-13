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


# the API caches BigQuery for 10 minutes too
@st.cache_data(ttl=600)
def get(path: str) -> dict | list:
    # long timeout, the API may need a cold start
    response = requests.get(f"{API_URL}{path}", timeout=60)
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="S&P 500 Volatility Forecast")
st.title("S&P 500 volatility, next 5 trading days")

with st.spinner("Loading, the service may need a few seconds to wake up."):
    forecast = get("/predict")
    model = get("/model")
    # columns also for an empty list, before the first batch run
    rows = pd.DataFrame(
        get("/predictions"),
        columns=["date", "prediction", "har_rv", "rv_20d", "vix_scaled", "actual"],
    )


def label(name: str) -> str:
    return LINES[name][0]


def get_range(dates: list, preset: str) -> tuple:
    days = PRESETS[preset] or len(dates)
    return dates[max(len(dates) - days, 0)], dates[-1]


def apply_preset(dates: list) -> None:
    if st.session_state.preset:
        st.session_state.range = get_range(dates, st.session_state.preset)


st.metric("Forecast", f"{forecast['prediction']:.1f} %")
st.caption(
    f"Model version {model['model_version']} (trained until {model['train_end']}) · "
    f"features as of {forecast['features_date']} · VIX {forecast['vix']:.1f} · "
    f"drift: {', '.join(model['drifted']) or 'none'}"
)
if forecast["stale"]:
    st.warning("Data is older than expected, the feature pipeline may have failed.")

# the API calls the model forecast "prediction" here
chart = rows.rename(columns={"prediction": "model"}).set_index(pd.to_datetime(rows["date"]))
# a slider needs two days, the first batch run writes one
if len(chart) > 1:
    dates = list(chart.index.date)
    st.session_state.setdefault("preset", "3 months")
    st.session_state.setdefault("range", get_range(dates, "3 months"))
    st.segmented_control("Range", list(PRESETS), key="preset", on_change=apply_preset, args=[dates])
    # a moved slider is no preset anymore
    start, end = st.slider(
        "Range",
        min_value=dates[0],
        max_value=dates[-1],
        key="range",
        format="YYYY-MM-DD",
        label_visibility="collapsed",
        on_change=lambda: st.session_state.update(preset=None),
    )
    chart = chart.loc[pd.Timestamp(start) : pd.Timestamp(end)]
lines = st.pills(
    "Lines", list(LINES), selection_mode="multi", default=list(LINES), format_func=label
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

mae = pd.DataFrame(
    [model["test_mae"], model["live_mae"]],
    index=["Test (12 months after training)", f"Live ({model['live_days']} days)"],
)
forecasts = [name for name in LINES if name != "actual"]
st.table(mae[forecasts].rename(columns=label).style.format("{:.2f}", na_rep="–"))

st.caption(
    "Annualized volatility of SPY in percent. Each point is the forecast made on that day for the "
    "next 5 trading days, the actual value is known 5 trading days later. Not a trading signal."
)
