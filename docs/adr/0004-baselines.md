# 4. Baselines

## Context

Beating the 20-day volatility is too easy.
The review suggests HAR-RV as a stronger baseline.
The VIX is the volatility the market expects for the next 30 days ([Cboe](https://markets.cboe.com/tradable_products/vix/faqs)).
It is usually higher than what really happens, because investors pay extra for protection (risk premium).

## Decision

- HAR-RV ([Corsi 2009](https://doi.org/10.1093/jjfinec/nbp001)): linear regression on the volatility of the last 1, 5 and 22 days

$$\hat{y}_t = \beta_0 + \beta_1 \mathrm{RV}_t^{(1)} + \beta_2 \mathrm{RV}_t^{(5)} + \beta_3 \mathrm{RV}_t^{(22)}$$

- VIX times one factor to remove the risk premium: average label divided by average VIX

$$c = \frac{\bar{y}}{\overline{\mathrm{VIX}}} \approx 0.8, \qquad \hat{y}_t = c \cdot \mathrm{VIX}_t$$

- No time conversion for the VIX, VIX and label are both in percent per year
- HAR-RV and the factor are fitted on the same data as the model, never on test
- Success: lower MAE than HAR-RV on test (last 12 months, ADR 9), instead of 10 % better than the 20-day volatility
- The scaled VIX is only reported
- Table per year with model, 20-day volatility, HAR-RV and scaled VIX, fitted on train only, over val and test
- Each year split into calm days ($\mathrm{VIX}_t \le 20$) and stressed days ($\mathrm{VIX}_t > 20$)
- Each training run writes the table to its log

## Consequences

- New features `rv_1d` and `rv_22d`
- The VIX can be compared fairly with the model
- In the table, val chose the number of trees, so the model looks a bit better there
- The table shows if the model only works when markets are calm
