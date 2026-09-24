#set page(paper: "a4", margin: 2cm)
#set text(font: "Libertinus Serif", size: 11pt)
#set heading(numbering: "1.")
#set par(justify: true)

#align(center)[
  #text(size: 18pt, weight: "bold")[Project Proposal - S&P 500 Realized Volatility Forecast]
  #v(0.3em)
  #text(size: 12pt)[I.BA_MLOPS_MM.H26]
  #v(0.1em)
  #text(size: 10pt)[Dominic Bieri]
  #v(0.1em)
  #text(size: 10pt)[#link("https://github.com/dominic-bieri/mlops")]
]

#v(1em)

= Problem statement

The goal is to predict how much the S&P 500, tracked through the SPY ETF, will move over the next 5 trading days (one trading week). This is called realized volatility. The forecast is updated once per trading day, after the US market closes.
Realized volatility shows how much the price moved over a period, no matter the direction. The project only looks at the S&P 500, using daily data from 1993 to today.
This is useful for risk managers, who need to know if the market will be calm or shaky.
It is also useful for long-term investors, who use volatility to decide when a sell-off is a good time to buy.

Success criterion: the model's MAE (mean absolute error) should be at least 10% lower than a simple baseline.
The baseline is the realized volatility of the last 20 trading days (one trading month). The model will be tested on data from 2024 to today.
It will also be compared to the VIX, an index that shows what the market itself expects future volatility to be.

= Originality & motivation

I am personally interested in financial markets and investing, especially in the overall market rather than single stocks or crypto.
That interest is why I chose this project.
Most finance projects try to predict the direction of prices, but that is close to a random walk and very hard for a model to get right, especially in a student project.
Volatility behaves differently.
Calm and turbulent periods tend to come in clusters, so there is a more realistic pattern for a model to learn.
This is why I focus on volatility instead of price direction.
It is still directly useful for risk management and for investors who want to know when to buy during a sell-off.

The model is also compared directly to the VIX, the market's own volatility forecast.
So the real question is not just whether the model beats a simple rolling average, but whether it adds anything beyond what the market already expects.

= Data source & features

The VIX (VIXCLS) comes from FRED, the data service of the St. Louis Fed, pulled through its API once per trading day, in the morning after the close, once available.
Instead of the raw S&P 500 index, the project tracks the SPY ETF, since the index itself is a licensed product of S&P Dow Jones Indices with reproduction restrictions, while ETF share price data carries no such restriction. SPY prices come from Tiingo, a free end-of-day stock data API, pulled once per trading day for that day's value only, handled through the API's date query parameter rather than filtered in code. Yahoo Finance is kept as a backup data source in case Tiingo or FRED becomes unavailable.
SPY has traded since 1993, so the historical backfill (loaded once from Tiingo and stored as a fixed snapshot) starts there instead of 1990.
This gives around 8500 daily rows going back to 1993, growing by roughly 252 rows per year.

The label is the realized volatility of the next 5 trading days, computed from daily log returns.
It only uses returns that come after the current day. None of the features contain these returns, so the label cannot be derived from them.
The features are the realized volatility over the last 5, 10, 20 and 60 days, the daily log return and its absolute value, and the VIX level and its recent change, all pre-calculated once per day as batch features.
All rolling windows only look backwards in time. The model will be trained on data through 2023 and tested on 2024 to today, in time order, with a 5 trading day gap so the label windows do not overlap.
This is a regression task, so there is no rare class to handle.

#pagebreak(weak: true)

= System design

The system follows the feature, training and inference (FTI) split shown below.

#figure(
  image("media/System_Design.svg", width: 100%),
)

== Core

The feature pipeline fetches the new S&P 500 and VIX values once per trading day and computes the features (batch processing).
The training pipeline reads the features, retrains a LightGBM model from scratch each week (automated stateless retraining) using the natural label from realized volatility, and registers the best version.
The inference pipeline loads the latest model and computes the 5 day forecast on request (online prediction with batch features), showing it next to the baseline and the VIX.

== Tech stack

/ BigQuery: stores the daily S&P 500 and VIX rows and the computed features in one growing table, used by both the training and inference pipeline
/ Agent Platform (formerly Vertex AI): logs each training run with its parameters and metrics, and holds the versioned models in its model registry
/ GitHub Actions: runs the daily feature pipeline job and the weekly training pipeline job on a schedule, plus manual triggers
/ FastAPI on Cloud Run: serves the 5 day forecast next to the baseline and the VIX; a small web page shows the current model version

All four services stay within their free monthly tier at this scale, or cost at most a few cents, well within the student GCP credits.

== Optional

A feature drift check and Terraform for the GCP resources will only be added if there is time left.
