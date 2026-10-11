# 3. SPY prices and dividends

## Context

SPY pays a dividend four times a year. On that day, the price drops by about the dividend amount.
Without a correction, this looks like a real price move and makes the volatility too high.
Tiingo offers an adjusted price (`adjClose`) that includes dividends.
But it changes all past prices every time a new dividend is paid, so stored data would no longer match the API.

## Decision

- Store the raw closing price (`close`) and the dividend of the day (`div_cash`), not `adjClose`
- When computing daily returns, add the dividend back on dividend days
- No correction for stock splits, because SPY never had one
- No historical "as known back then" data (e.g. from ALFRED): VIX and SPY prices are not changed after they are published

## Consequences

- Stored prices never change afterwards
- The return calculation has to handle dividends itself
