# 4. Baselines

## Context

Beating the 20-day volatility is too easy.
The review suggests HAR-RV as a stronger baseline.
The VIX shows the volatility the market expects for the next 30 days ([Cboe](https://markets.cboe.com/tradable_products/vix/faqs)).
It is usually higher than the volatility that really happens, because investors pay extra for protection.

## Decision

- HAR-RV ([Corsi 2009](https://doi.org/10.1093/jjfinec/nbp001)): linear regression on the volatility of the last 1, 5 and 22 days

$$\hat{y}_t = \beta_0 + \beta_1 \mathrm{RV}_t^{(1)} + \beta_2 \mathrm{RV}_t^{(5)} + \beta_3 \mathrm{RV}_t^{(22)}$$

- No conversion of the VIX for the different time span, VIX and label are both in percent per year
- The VIX is multiplied by one factor to remove the risk premium: the average label divided by the average VIX

$$c = \frac{\bar{y}}{\overline{\mathrm{VIX}}} \approx 0.8, \qquad \hat{y}_t = c \cdot \mathrm{VIX}_t$$

- HAR-RV and the factor are fitted on the same data as the model, never on test
- Model, 20-day volatility, HAR-RV and scaled VIX in one table per year, all fitted on train only, over val and test
- Each training run saves the table as `errors_by_year.csv` in the model bucket
- Each year split into calm days ($\mathrm{VIX}_t \le 20$) and stressed days ($\mathrm{VIX}_t > 20$)
- Success criterion: on the test window (last 12 months, ADR 9), the model has a lower MAE than HAR-RV (instead of 10 % better than the 20-day volatility)
- The scaled VIX is only reported, not part of the criterion

## Consequences

- New features `rv_1d` and `rv_22d`
- The VIX can be compared fairly with the model
- HAR-RV and the factor don't use any test data
- In the table, val only chooses the number of trees, so the model is slightly favoured there
- The table shows if the model only works when markets are calm
