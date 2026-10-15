#set page(paper: "a4", margin: 2cm)
#set text(font: "Libertinus Serif", size: 11pt)
#set par(justify: true)
#set heading(numbering: "1.")

#let repo = "https://github.com/dominic-bieri/mlops"
#let file(path) = link(repo + "/blob/main/" + path, raw(path))

#align(center)[
  #text(size: 18pt, weight: "bold")[MS2 Summary - S&P 500 Realized Volatility Forecast]
  #v(0.3em)
  #text(size: 12pt)[I.BA_MLOPS_MM.H26]
  #v(0.1em)
  #text(size: 10pt)[Dominic Bieri]
]

= What I achieved in this milestone

- *Works now:* The feature pipeline runs in GitHub Actions every morning after a US trading day (Tue–Sat, 13:00 UTC). It loads SPY prices from Tiingo and the VIX from FRED into BigQuery and then builds the feature table with the label. If a table is empty, it loads all data since 1993.
- *Works now:* Terraform deploys the BigQuery tables. GitHub Actions runs it when a merge to `main` changes `terraform/`. On every pull request, CI runs ruff, pytest and the Terraform checks.
- *Decision:* I compute the volatility from open, high, low and close. With only 5 daily returns the label was too noisy.
- *Decision:* There are three BigQuery tables. `vix` and `sp500` hold the raw data, so a run only fetches the last few days and not the whole history. Rows are only added, and each row stores when it was first loaded. `features` is rebuilt from the raw tables on every run. It is small, and the labels of the last 5 days have to be filled in later anyway.
- *Decision:* The model now has to beat HAR-RV and the scaled VIX, not just be 10 % better than the 20-day baseline. From 2024 on, HAR-RV is already 17 % better than the 20-day baseline (MAE 3.88 vs. 4.68), and the scaled VIX is about as good (3.84). The numbers come from #file("src/sp500_vol/evaluation/baselines.py").
- *What it cost:* The Terraform deployment took a lot of time. GitHub Actions logs in to Google Cloud with Workload Identity Federation, so there is no stored key. Each workflow has its own GitHub environment with only the Google roles it needs, and the login only works on `main`. I want to reuse this later for Agent Platform and Cloud Run.
- *Not done yet:* There is no model yet. Training, the model column in the yearly table (A1, B1) and inference come in MS3.
- *Look at first:* #file("src/sp500_vol/features/build.py") for features and label, #file("tests/test_replay.py") for the day-by-day check, #file("src/sp500_vol/evaluation/baselines.py") for the baseline errors.

= Response to MS1 reviews

More details are in the ADRs in #link(repo + "/tree/main/docs/adr")[`docs/adr`].

- *E1, B2: Define the RV label and address its noise* - Changed \
  For each day I compute a variance from open $O$, high $H$, low $L$ and close $C$ and the jump from the previous close (Garman-Klass-Yang-Zhang). This uses more of the day than the close alone, so the 5-day label is less noisy. On dividend days I add the dividend $D$ back to the open.
  $ v_t = ln^2 ((O_t + D_t) / C_(t-1)) + 1/2 ln^2 (H_t / L_t) - (2 ln 2 - 1) ln^2 (C_t / O_t), quad "RV"_t^((n)) = 100 sqrt(252/n sum_(i=0)^(n-1) v_(t-i)) $
  The label is $y_t = "RV"_(t+5)^((5))$. The 20-day baseline $"RV"_t^((20))$ uses the same formula, and the VIX is compared with this label (A2). \
  Files: #file("docs/adr/0006-volatility-definition.md"), #file("src/sp500_vol/features/build.py")
- *A1: Add HAR-RV as a second baseline* - Partly \
  HAR-RV is a linear regression on the volatility of the last 1, 5 and 22 days, fitted on the training data:
  $ hat(y)_t = beta_0 + beta_1 "RV"_t^((1)) + beta_2 "RV"_t^((5)) + beta_3 "RV"_t^((22)) $
  I now store `rv_1d` and `rv_22d`. A script prints the errors per year for the 20-day baseline, HAR-RV and the VIX. The model column comes with training in MS3. \
  Files: #file("src/sp500_vol/features/build.py"), #file("src/sp500_vol/evaluation/baselines.py")
- *A2: Make the VIX comparable* - Changed \
  The VIX and the label are both in percent per year, so I don't rescale to 5 days. Because of the risk premium the VIX is higher than the realized volatility. I multiply it by one factor #box($c = overline(y) \/ overline("VIX") = 0.80$) from the training data (until 2023), so the benchmark is #box($hat(y)_t = c dot "VIX"_t$). \
  Files: #file("docs/adr/0007-baselines.md"), #file("src/sp500_vol/evaluation/baselines.py")
- *B3: Forecast issue time and label maturity* - Changed \
  The forecast for day $t$ is made at 13:00 UTC the next morning (Tue–Sat), before the US market opens. The raw tables store `loaded_at`, the time a row was first loaded. Training only uses rows where all 5 future days are known. \
  Files: #file("docs/adr/0008-issue-time-and-label-maturity.md"), #file("src/sp500_vol/features/ingest.py"), #file("src/sp500_vol/evaluation/baselines.py")
- *B4: Training, promotion and retraining cadence* - Changed \
  LightGBM with L1 loss, because I measure success with MAE. I pick the parameters from a small grid, training until 2020 and validating on 2021 to 2023. The test from 2024 runs once with a fixed model. Retraining is monthly, because a week only adds 5 rows. A new model replaces the current one only if its MAE on the last 3 months is lower than that of the current model, HAR-RV and the scaled VIX. Then it is trained again on all data. \
  Files: #file("docs/adr/0009-training-and-retraining.md")
- *B1: Scope of the output* - Partly \
  The README says that the forecast is SPY volatility as a proxy for the S&P 500, not a trading signal. The A1 table splits each year into calm days #box($"VIX"_t <= 20$) and stressed days #box($"VIX"_t > 20$). The model column comes in MS3. \
  Files: #file("README.md"), #file("src/sp500_vol/evaluation/baselines.py")
- *B8: Diagram arrow* - Changed \
  I added an arrow from the BigQuery feature store to the inference pipeline. \
  Files: #file("docs/media/System_Design.svg")
- *B9: Tracker choice and one-line why's* - Changed \
  For each tool there is one line why I chose it over an alternative. \
  Files: #file("docs/adr/0001-tool-choice.md")
- *B10: Historical replay test* - Changed \
  A test runs the pipeline day by day for normal days, a market shock and a late VIX. It checks that old features don't change, labels only appear after 5 days and `loaded_at` is set. \
  Files: #file("tests/test_replay.py")
- *B5, B6, B7: OpenAI news stage, agent workflows, LSTM comparison* - Rejected \
  The editorial summary did not confirm these points, and they are not part of the proposal. I stay with LightGBM against the baselines.
