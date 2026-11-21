#set page(paper: "a4", margin: 2cm)
#set text(font: "Libertinus Serif", size: 11pt)
#set par(justify: true)
#set heading(numbering: "1.")

#let repo = "https://github.com/dominic-bieri/mlops"
#let file(path) = link(repo + "/blob/main/" + path, raw(path))

#align(center)[
  #text(size: 18pt, weight: "bold")[MS3 Summary - S&P 500 Realized Volatility Forecast]
  #v(0.3em)
  #text(size: 12pt)[I.BA_MLOPS_MM.H26]
  #v(0.1em)
  #text(size: 10pt)[Dominic Bieri]
]

= What I achieved in this milestone

- *Works now:* The training pipeline. cron-job.org starts it on the 1st of each month, I can also start it by hand. It trains LightGBM on the newest feature snapshot. Parameters, the dates of train, val and test and the test MAE of the model and all baselines are logged in Agent Platform Experiments.
- *Decision:* Agent Platform Experiments instead of MLflow or W&B. It is in the same Google Cloud project as the data and the Model Registry, so there is no own server to run and no extra login (ADR 6).
- *Decision:* A new model has to beat HAR-RV and must not be worse than the current champion. Both are scored on the same newest 12 months, which neither has seen, so the comparison is fair. A champion older than 6 months does not count, so an old model can't block new ones forever (ADR 6).
- *Works now:* Each model version stores its snapshot, commit and run. Next to the model a `metadata.json` holds the fitted baselines, so the inference uses the same ones.
- *Works now:* Each run writes its results and the calm and stressed table (B3) to the job summary on its run page. So nobody needs access to my Google Cloud.
- *Works now:* The inference is done too. After each feature run a batch job forecasts the new days with the champion, writes them to BigQuery and checks drift with the PSI per feature. API and UI run on Cloud Run (ADR 7).
- *Works now:* I updated the system diagram. Yahoo Finance is gone, each pipeline shows when it runs and the API and the table with predictions and drift are new (#file("docs/media/System_Design.svg")).
- *What it cost:* The A1 fix changes `vix_change_5d` on the days after 33 holidays and drops 2 days in 1997 and the day 5 after each.
- *Risk:* If cron-job.org does not start a run at all, no run fails. The API marks the data as stale after 5 days and the UI shows a warning (ADR 5).
- *Look at first:* #file("src/sp500_vol/training/train.py"), #file("src/sp500_vol/common/registry.py"), #file("docs/adr/0006-training-and-retraining.md") and the job summary of a training run.

= Response to MS2 reviews

More details are in the ADRs in #link(repo + "/tree/main/docs/adr")[`docs/adr`].

- *A1: `vix_change_5d` does not always span five trading days* - Changed \
  I put the VIX on the SPY trading days first and shift it after that. A VIX on a market holiday is ignored now. There are 34 such days since 1993, 33 of them since 2022. If a SPY day has no VIX, that day and the day 5 later are dropped. This happened twice, both in 1997. A new test has a VIX on a day without SPY. `features` is built again on every run, so the whole history was fixed without a migration. \
  Files: #file("src/sp500_vol/features/build.py"), #file("tests/test_build.py"), #file("docs/adr/0002-feature-store.md")
- *B1, A2: A green run does not mean fresh features* - Partly \
  My logs show it too. On 24.10, 31.10 and 07.11 the Saturday run had no Friday VIX, it only came with the Tuesday run. The feature pipeline now runs every day. After the build a check looks at the NYSE calendar (`exchange_calendars`). One trading day behind gives a warning, two or more make the run fail. Only a warning at one day, because the Friday VIX is late almost every week and a red run every Saturday would soon be ignored. The inference starts anyway. \
  Not done: a separate check with its own schedule (B1). It would need a scheduler too. On cron-job.org it fails together with the runs, and GitHub `schedule` is the one I replaced because it was late or skipped (ADR 5). A run that never starts is still visible. The API marks the data as stale after 5 days and the UI shows a warning. \
  Files: #file("src/sp500_vol/features/validate.py"), #file("tests/test_validate.py"), #file("src/sp500_vol/inference/api.py"), #file("docs/adr/0005-issue-time-and-label-maturity.md")
- *B2: Short API errors stop the run and the Yahoo backup is missing* - Changed \
  Both clients retry 3 times on 429 and 5xx and wait at most 60 seconds for `Retry-After`. If an API is down for longer, the next daily run gets the data. I removed Yahoo Finance from the diagram and the README, Tiingo and FRED were reliable enough. \
  Files: #file("src/sp500_vol/features/http.py"), #file("tests/test_clients.py"), #file("docs/media/System_Design.svg")
- *B3: The calm and stressed table needs context* - Changed \
  The table has one row per split, year and calm or stressed days (VIX above 20), with the number of days. Val uses the tuned model and baselines fitted on train. Test uses the model trained again on train and val, with baselines fitted on train and val. Every training run writes all rows to its job summary. Here are the test rows of the last training run, the val rows are on its run page. The model beats HAR-RV in every row. Only on the 6 stressed days in 2025 the scaled VIX is better.

  #table(
    columns: 7,
    align: (left, left, right, right, right, right, right),
    [*Year*], [*Days*], [*n*], [*Model*], [*20-day*], [*HAR-RV*], [*Scaled VIX*],
    [2025], [calm], [26], [2.81], [5.18], [3.55], [3.93],
    [2025], [stressed], [6], [4.91], [6.00], [6.91], [4.62],
    [2026], [calm], [178], [2.86], [3.71], [3.18], [3.30],
    [2026], [stressed], [41], [3.19], [3.24], [3.42], [3.61],
  )
  Files: #file("src/sp500_vol/training/train.py"), #file("tests/test_model.py"), #file("docs/adr/0004-baselines.md")
- *A3: Corrected values are discarded* - Rejected \
  The 7 days overlap is for late values, not for corrections. I compared the whole history once with the sources. My values are the same as the source today, for 8,543 VIX days and 8,511 SPY days. In the FRED archive (ALFRED) 11 VIX days were changed later, all on 2021-06-03 and one again on 2024-08-12. All of them were years old, so a log over the 7 days overlap would not have seen any of them. Tiingo keeps no old versions. I store raw prices and the dividend, not `adjClose`, so a dividend does not change old rows (ADR 1). The raw tables stay append only, so I can still compute what the pipeline knew on a past day. That is also why I don't add `--start` and `--end`. A wrong value I would delete by hand and the next run loads it again. A plausible but wrong value is not caught by the checks. I would only see it as an outlier in the UI or when I repeat the comparison with the source. \
  Files: #file("docs/adr/0001-raw-data.md")
- *E1: Editorial in the public repository* - Changed \
  I removed the MS1 editorial PDF with a rewrite of the Git history.
- *E2: Snapshot retention* - Changed \
  After each run the feature pipeline deletes all snapshots, except the newest and those a model was trained on. Older features can be built again from the append-only raw tables. \
  Files: #file("src/sp500_vol/features/snapshots.py"), #file("tests/test_snapshots.py"), #file("docs/adr/0002-feature-store.md")
- *E3: Git LFS* - Rejected \
  Git LFS is already under Requirements in the README, with the install link. `git lfs install` is a one time setup per machine, not per repository, and the install page shows it. On GitHub the PDFs and the diagrams open without it. \
  Files: #file("README.md")
