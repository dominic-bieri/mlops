# 2. Raw data tables

## Context

The data comes from two sources: VIX from FRED and SPY prices from Tiingo.
The two sources do not always have values for the same days, and one source can fail while the other works.
The proposal planned one table for all data and features.

## Decision

- Raw data goes into two tables, `vix` and `sp500`, one row per day (`date`)
- Features get their own table ([ADR 5](0005-feature-table.md))

## Consequences

- Each source is loaded on its own; if one fails, the other table is still correct
- To build features, the two tables have to be joined on `date`
