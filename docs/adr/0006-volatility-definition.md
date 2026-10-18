# 6. Volatility definition

## Context

The label, the 20-day baseline and the VIX comparison should all use the same volatility.
With closing prices only, the 5-day label is based on just 5 returns and is very noisy.
Tiingo also delivers open, high and low, which show how much the price moved during the day.
I compared the common range-based estimators (Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang) to find one that is accurate and still simple.

## Decision

- Garman-Klass-Yang-Zhang ([LuxAlgo](https://www.luxalgo.com/library/concept/garman-klass-yang-zhang-hybrid/), [Medium](https://derivvaluation.medium.com/garman-klass-yang-zhang-historical-volatility-calculation-volatility-analysis-in-python-2c83d3be20be)), variance over the last $n$ days

$$\sigma^2 = \frac{1}{n}\sum_{i=1}^{n}\left[\left(\ln\frac{O_i}{C_{i-1}}\right)^2 + \frac{1}{2}\left(\ln\frac{H_i}{L_i}\right)^2 - (2\ln 2 - 1)\left(\ln\frac{C_i}{O_i}\right)^2\right]$$

- $O_i, H_i, L_i, C_i$: open, high, low, close of day $i$, on dividend days the dividend is added to $O_i$ (ADR 3)
- First part: overnight jump from yesterday's close, the rest: move during the day (Garman-Klass)
- $\ln$ of a ratio is about the move in percent, squared so only the size counts, not the direction
- Volatility over $n$ days in percent per year, like the VIX

$$\mathrm{RV}_t^{(n)} = 100\sqrt{252 \cdot \sigma^2}$$

- $\cdot 252$: per year, $\sqrt{\ }$: standard deviation, $\cdot 100$: percent
- Example: $\mathrm{RV} = 20$ means the price moves about 20 % in a normal year
- Label: $y_t = \mathrm{RV}_{t+5}^{(5)}$, the volatility of days $t+1$ to $t+5$
- Same function for all of these, so they are on the same scale:
  - Features `rv_1d` to `rv_60d`: how calm the market was up to day $t$
  - Label `rv_next_5d`: what the model predicts
  - Baselines: `rv_20d` as forecast, HAR-RV on `rv_1d`, `rv_5d`, `rv_22d`
- Why this one: it gives one value per day, so it is simple to use for any window, and unlike Parkinson and Garman-Klass it includes the overnight jump from the previous close

## Consequences

- Less noise in the label than with closing prices only
- About the same level as with closing prices, so the VIX comparison still works
- `sp500` also stores open, high and low
