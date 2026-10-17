# 6. Volatility definition

## Context

The label, the 20-day baseline and the VIX comparison should all use the same volatility.
With closing prices only, the 5-day label is based on just 5 returns and is very noisy.
Tiingo also delivers open, high and low, which show how much the price moved during the day.
I found the formula below with Claude and my own research.
There are other range-based estimators (Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang).

## Decision

- Daily variance $v_t$ with the Garman-Klass-Yang-Zhang formula ([overview of the estimators](https://portfoliooptimizer.io/blog/range-based-volatility-estimators-overview-and-examples-of-usage/)), in two parts: overnight jump + move during the day

$$v_t = \underbrace{j_t^2}_{\text{overnight}} + \underbrace{0.5\,h_t^2 - 0.39\,c_t^2}_{\text{during the day (Garman-Klass)}}$$

- $j_t = \ln\frac{O_t + D_t}{C_{t-1}}$: yesterday's close -> today's open, dividend added back (ADR 3)
- $h_t = \ln\frac{H_t}{L_t}$: today's low -> today's high
- $c_t = \ln\frac{C_t}{O_t}$: today's open -> today's close
- $\ln$ of a ratio is about the move in percent, squared so only the size counts, not the direction
- Weights from Garman-Klass, $0.39 \approx 2\ln 2 - 1$ (code uses the exact value)
- Volatility over $n$ days in percent per year, like the VIX

$$\mathrm{RV}_t^{(n)} = 100\sqrt{252 \cdot \bar{v}}$$

- $\bar{v}$: mean of $v$ over the last $n$ days, $\cdot 252$: per year, $\sqrt{\ }$: standard deviation, $\cdot 100$: percent
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
