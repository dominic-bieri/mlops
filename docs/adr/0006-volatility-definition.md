# 6. Volatility definition

## Context

The label, the 20-day baseline and the VIX comparison should all use the same volatility.
With closing prices only, the 5-day label is based on just 5 returns and is very noisy.
Tiingo also delivers open, high and low, which show how much the price moved during the day.
I found the formula below with Claude and my own research.
There are other range-based estimators (Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang).

## Decision

- Daily variance with the Garman-Klass-Yang-Zhang formula ([overview of the estimators](https://portfoliooptimizer.io/blog/range-based-volatility-estimators-overview-and-examples-of-usage/)): open $O$, high $H$, low $L$, close $C$ and the jump from the previous close, with the dividend $D$ added back to the open (ADR 3)

$$j_t = \ln\frac{O_t + D_t}{C_{t-1}}, \quad h_t = \ln\frac{H_t}{L_t}, \quad c_t = \ln\frac{C_t}{O_t}$$

$$v_t = j_t^2 + \frac{1}{2}h_t^2 - (2\ln 2 - 1)\,c_t^2$$

- Volatility over $n$ days in percent per year, like the VIX

$$\mathrm{RV}_t^{(n)} = 100\sqrt{\frac{252}{n}\sum_{i=0}^{n-1} v_{t-i}}$$

- Label: $y_t = \mathrm{RV}_{t+5}^{(5)}$, the volatility of the next 5 days
- Same function for features, label and baseline
- Why this one: it gives one value per day, so it is simple to use for any window, and unlike Parkinson and Garman-Klass it includes the overnight jump from the previous close

## Consequences

- Less noise in the label than with closing prices only
- About the same level as with closing prices, so the VIX comparison still works
- `sp500` also stores open, high and low
