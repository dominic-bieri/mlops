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

// TODO

= System design

// TODO