# 7. Baselines

## Context

The VIX shows the volatility the market expects for the next 30 days ([Cboe](https://markets.cboe.com/tradable_products/vix/faqs)).
It is usually higher than the volatility that really happens, because investors pay extra for protection.

## Decision

- No conversion of the VIX for the different time span, VIX and label are both in percent per year
- The VIX is multiplied by one factor to remove the risk premium: the average label divided by the average VIX

$$c = \frac{\bar{y}}{\overline{\mathrm{VIX}}} \approx 0.8, \qquad \hat{y}_t = c \cdot \mathrm{VIX}_t$$

- The factor is fitted on training data only

## Consequences

- The VIX can be compared fairly with the model
- The factor doesn't use any test data
