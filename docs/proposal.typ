#set page(paper: "a4", margin: 2cm)
#set text(font: "Arial", size: 11pt)
#set heading(numbering: "1.")
#set par(justify: true)

#align(center)[
  #text(size: 18pt, weight: "bold")[Project Proposal - S&P 500 Realized Volatility Forecast]
  #v(0.3em)
  #text(size: 12pt)[MLOPS - HS26]
  #v(0.1em)
  #text(size: 10pt)[Dominic Bieri]
  #v(0.1em)
  #text(size: 10pt)[#link("https://github.com/dominic-bieri/mlops")]
]

#v(1em)

= Problem statement

Predict the annualized realized volatility of the S&P 500 (^GSPC) for the next 5 trading days (one trading week), updated once per trading day after US market close.
Realized volatility measures how much the price actually moved over a period, regardless of direction. Scope: S&P 500 index only, daily data from 1990 to today.
This is useful for risk managers, who need to know how calm or choppy the market is likely to be, and for long-term (value) investors, who use volatility to judge when panic-driven sell-offs create buying opportunities.

Success criterion: the model's MAE should be at least 10% lower than a simple baseline, the realized volatility of the last 20 trading days (one trading month), tested on data from 2024 to today.
Also compared against the VIX, an index reflecting the market's own volatility expectation.

= Originality & motivation

I have a personal interest in financial markets and investing, especially in looking at the overall market rather than individual stocks or crypto.
That's what led me to this project.
Most finance projects try to predict price direction, but that's close to a random walk and very hard for a model to get right, especially for a student project.
Volatility behaves differently. Calm and turbulent periods tend to cluster, so it's a more realistic pattern to actually learn.
That's why I focus on volatility instead of price direction, and it's still directly useful for risk management and for investors deciding when to buy during a sell-off.

It's also benchmarked directly against the VIX, the market's own volatility forecast.
So the real question becomes whether the model adds anything beyond what's already priced in, not just whether it beats a rolling average.

= Data source & features

Both series will come from FRED, the data service of the St. Louis Fed. The S&P 500 (SP500) and the VIX (VIXCLS) will be pulled through its API once per trading day, the morning after the close, when both values are available.
FRED only keeps ten years of S&P 500 history, so everything up to the end of 2016 will be loaded once from Yahoo Finance and stored as a fixed snapshot.
This gives around 9000 daily rows going back to 1990, growing by roughly 252 rows a year.

The label will be the realized volatility of the next 5 trading days, computed from daily log returns.
It only uses returns after the current day, which none of the features contain, so it cannot be derived from them.
The features will be the realized volatility over the last 5, 10, 20 and 60 days, the daily log return and its absolute value, and the VIX level and its recent change.
All rolling windows will only look backwards. Training will use data through 2023 and testing 2024 to today, in time order, with a gap of 5 trading days so the label windows do not overlap.
As a regression task, there is no rare class to handle.

= System design

The system will follow the feature, training and inference (FTI) split shown below.

// TODO diagram

== Core

The feature pipeline will fetch the new S&P 500 and VIX values once per trading day, compute the features and store them.
The training pipeline will read the features, train a LightGBM model and register the best version.
The inference pipeline will load the latest model and show the 5 day forecast next to the baseline and the VIX.

== Tech stack

/ BigQuery: stores the daily S&P 500 and VIX rows and the computed features, one growing table used by both the training and inference pipeline
/ Google's Agent Platform (formerly Vertex AI): logs each training run with its parameters and metrics, holds the versioned models in its model registry
/ GitHub Actions: runs the daily feature pipeline job and the weekly training pipeline job on a schedule, plus manual triggers
/ FastAPI on Cloud Run: serves the 5 day forecast next to the baseline and the VIX, small web page shows the current model version

All four services stay within their free monthly tier at this scale, or cost at most a few cents, well within the student GCP credits.

== Optional

A feature drift check and Terraform for the GCP resources will only be added if time allows.
