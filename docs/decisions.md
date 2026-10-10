# Design decisions

## VIX

- VIX = market's expected volatility for the next 30 days
- Used as feature, includes upcoming events (e.g. Fed meetings)
- Raw VIX usually too high, so benchmark is a linear regression `volatility = a + b * VIX`
- Optional: model without VIX

## Training

- Only data up to day `t`, label = volatility of next 5 trading days
- Missing VIX: same handling in training and prediction (e.g. previous day)
- Volatility and label in yearly %, same as VIX
- Benchmark regression fitted on data up to 2023 only
- Predict only once VIX of day `t` is on FRED (published next morning)
- Benchmark regression is an extra comparison, the success criterion stays the same (MAE at least 10% below the 20 day baseline)

## Data

- Raw data in two tables `vix` and `sp500`, keyed on `date` (proposal: one table); features will get their own table
- SPY stored as raw `close` plus `div_cash`, not Tiingo's `adjClose`: `adjClose` is changed back in time with every new dividend, so it does not fit a fixed snapshot
- Log returns must add the dividend back on ex-dividend days, otherwise there is a fake price drop
- VIXCLS and SPY prices are market data and are not revised later, so today's values are the same as what was known back then (no point-in-time data from ALFRED needed)
- SPY never had a split, so no split adjustment is needed
- One ingest script for backfill and daily runs (proposal: only the current day): it starts 7 days before the latest stored date, or at 1993 if the table is empty. Upsert makes reloading safe, so missed days and late FRED values are filled in
