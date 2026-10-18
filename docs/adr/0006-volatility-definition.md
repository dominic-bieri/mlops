# 6. Volatility definition

## Context

The label, the 20-day baseline and the VIX comparison need the same volatility.
With only closing prices, the 5-day label uses just 5 numbers and jumps a lot.
Tiingo also has open, high and low. They show how much the price moved during the day.
Common formulas that use them: Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang.
I wanted one that is accurate and still simple.

## Decision

- Garman-Klass-Yang-Zhang ([LuxAlgo](https://www.luxalgo.com/library/concept/garman-klass-yang-zhang-hybrid/), [Medium](https://derivvaluation.medium.com/garman-klass-yang-zhang-historical-volatility-calculation-volatility-analysis-in-python-2c83d3be20be))

$$\sigma^2 = \frac{1}{n}\sum_{i=1}^{n}\left[\left(\ln\frac{O_i}{C_{i-1}}\right)^2 + \frac{1}{2}\left(\ln\frac{H_i}{L_i}\right)^2 - (2\ln 2 - 1)\left(\ln\frac{C_i}{O_i}\right)^2\right]$$

- $O_i, H_i, L_i, C_i$: open, high, low, close of day $i$. On dividend days the dividend is added to $O_i$ (ADR 3)
- $\ln$ of two prices is about the move in percent ($\ln\frac{101}{100} \approx 1\,\%$). Squared, so up and down count the same
- Three parts for each day:
  - Jump over night, from yesterday's close to today's open (e.g. news after the close). Added by Yang-Zhang
  - Move during the day, from low to high. Garman-Klass
  - Correction, makes the second part smaller. Garman-Klass
- Why the correction: if the price moves randomly, the second part is on average 1.39 ($2\ln 2$) times too big. The open-close part is on average right, so $1.39 - 0.39 = 1$
- Why not only open-close: also right on average, but jumps a lot. Low and high show the whole day, so the result is more stable
- $\frac{1}{n}\sum$: average over the last $n$ days
- In percent per year, like the VIX

$$\mathrm{RV}^{(n)} = 100\sqrt{252 \cdot \sigma^2}$$

- 252 trading days per year, square root turns variance into volatility, 100 for percent
- Example: $\mathrm{RV} = 20$ means the price moves about 20 % in a normal year
- Label: volatility of the next 5 days, $y_t = \mathrm{RV}_{t+5}^{(5)}$
- One function for features (`rv_1d` to `rv_60d`), label (`rv_next_5d`) and baselines (`rv_20d`, HAR-RV), so all have the same scale
- Why this formula: one value per day, so it works for any window. Unlike Parkinson and Garman-Klass it has the jump over night. Simpler than Yang-Zhang, which needs several days at once

## Consequences

- Label is less noisy than with closing prices only
- About the same level as with closing prices, so the VIX comparison still works
- `sp500` also stores open, high and low
- Assumes no trend during the day, with a strong trend the value is a bit off
