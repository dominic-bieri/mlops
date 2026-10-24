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

- *Works now:* Every morning after a US trading day (Tue–Sat, 10:00 New York time), GitHub Actions loads SPY prices from Tiingo and the VIX from FRED into BigQuery and builds the feature table with the label.
- *Works now:* Terraform creates the BigQuery tables. CI runs ruff, pytest and the Terraform checks on every pull request.
- *Decision:* The volatility uses open, high, low and close, not only the close. With 5 daily returns the label was too noisy.
- *Decision:* `sp500` and `vix` hold the raw data. Rows are only added, so a run only fetches the last few days. `features` is rebuilt on every run, because it is small and the labels of the last 5 days are filled in later. Each version is kept as a read-only BigQuery snapshot with the Git commit that built it, so a model can be traced to its data (ADR 2).
- *Decision:* The model has to beat HAR-RV, the scaled VIX is only reported. On the last 12 months (until 2026-10-08), HAR-RV (MAE 3.42) and the scaled VIX (3.46) are already better than the 20-day baseline (3.78).
- *What it cost:* Most time went into the deployment. GitHub Actions logs in to Google Cloud without a stored key (Workload Identity Federation), and each workflow only gets the roles it needs.
- *Risk:* GitHub Actions started scheduled runs 3–5 hours late or skipped them (#link("https://github.com/orgs/community/discussions/207346")[community discussion]). Now cron-job.org starts the workflow on time (ADR 5). A skipped run does no harm, the next run fills the gap.
- *Not done yet:* Training, inference and the model column in the yearly table (A1, B1) come in MS3.
- *Look at first:* #file("src/sp500_vol/features/build.py"), #file("tests/test_replay.py"), #file("src/sp500_vol/evaluation/baselines.py").

= Response to MS1 reviews

More details are in the ADRs in #link(repo + "/tree/main/docs/adr")[`docs/adr`].

- *E1, B2: Define the RV label and address its noise* - Changed \
  Daily variance from open, high, low, close and the overnight jump (Garman-Klass-Yang-Zhang, formulas in ADR 3). The label is the volatility of the next 5 days in percent per year, like the VIX. The 20-day baseline uses the same formula. Of the common estimators it is a good trade-off between accuracy and simplicity (ADR 3). \
  Files: #file("docs/adr/0003-volatility-definition.md"), #file("src/sp500_vol/features/build.py")
- *A1: Add HAR-RV as a second baseline* - Partly \
  A linear regression on the volatility of the last 1, 5 and 22 days, fitted on the training data (formula in ADR 4). A script prints the errors per year for the 20-day baseline, HAR-RV and the VIX. \
  Files: #file("docs/adr/0004-baselines.md"), #file("src/sp500_vol/features/build.py"), #file("src/sp500_vol/evaluation/baselines.py")
- *A2: Make the VIX comparable* - Changed \
  The VIX is higher than the realized volatility because of the risk premium. I scale it by 0.80, the average label divided by the average VIX on the training data (ADR 4). \
  Files: #file("docs/adr/0004-baselines.md"), #file("src/sp500_vol/evaluation/baselines.py")
- *B3: Forecast issue time and label maturity* - Changed \
  The forecast for a trading day is made the next morning at 10:00 New York time, because FRED usually publishes the VIX shortly after 9:30. The market is already open by then, but the forecast only uses data up to the previous close. Each raw row stores when it was first loaded (`loaded_at`). Training only uses rows where all 5 future days are known. \
  Files: #file("docs/adr/0005-issue-time-and-label-maturity.md"), #file("src/sp500_vol/features/ingest.py"), #file("src/sp500_vol/evaluation/baselines.py")
- *B4: Training, promotion and retraining cadence* - Changed \
  LightGBM with L1 loss, because success is measured with MAE. Retraining once a month on a rolling split (test: last 12 months), because fixed dates don't fit monthly retraining. Parameters are chosen on val. A new model is only registered if it beats HAR-RV on test. Details follow in MS3. \
  Files: #file("docs/adr/0006-training-and-retraining.md"), #file("src/sp500_vol/evaluation/baselines.py")
- *B1: Scope of the output* - Partly \
  The README says the forecast is SPY volatility as a proxy for the S&P 500, not a trading signal. The A1 table also splits calm and stressed days (VIX above 20). \
  Files: #file("README.md"), #file("src/sp500_vol/evaluation/baselines.py")
- *B8: Diagram arrow* - Changed \
  Arrow from the BigQuery feature store to the inference pipeline. \
  Files: #file("docs/media/System_Design.svg")
- *B10: Historical replay test* - Changed \
  A test runs the pipeline day by day for normal days, a market shock and a late VIX. It checks that old features don't change, labels only appear after 5 days and `loaded_at` is set. \
  Files: #file("tests/test_replay.py")
- *B9: Tracker choice and one-line why's* - Rejected \
  Everything should run in Google Cloud: one project, one login, one bill. Agent Platform is already accepted as an alternative to MLflow or W&B.
- *B5: Optional OpenAI news stage* - Rejected \
  News back to 1993 would need another licensed source. Without it, the feature only exists from the day the poller starts, so the model could not be trained on it for years. It would also add a paid API to the core pipeline.
- *B6: Agent workflows for coding and documentation* - Rejected \
  This is about how I develop, not about the ML system. It changes neither the data, the model nor the pipelines.
- *B7: LSTM comparison* - Rejected \
  With about 8,400 daily rows and 10 features, an LSTM has little to learn from, and HAR-RV is already a strong linear bar. LightGBM against the baselines stays the planned scope.
