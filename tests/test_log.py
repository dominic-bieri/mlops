from pathlib import Path

import pandas as pd
import pytest

from sp500_vol.common.log import github_summary, github_table


def test_summary_appends_markdown(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))

    github_summary("Features: new snapshot", ["Rows: 10", "Newest day: 2026-11-20"])
    github_summary("Inference: new forecast", ["Day: 2026-11-20"])

    text = path.read_text()
    assert text.startswith("### Features: new snapshot\n\n- Rows: 10\n- Newest day: 2026-11-20\n")
    assert "### Inference: new forecast\n\n- Day: 2026-11-20\n" in text


def test_summary_without_github_goes_to_the_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    with caplog.at_level("INFO"):
        github_summary("Training: no new model", ["Champion unchanged"])

    assert "### Training: no new model" in caplog.text


def test_table_is_markdown(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    df = pd.DataFrame({"split": ["test"], "year": [2026], "n": [42]})

    github_table("MAE per year", df)

    assert path.read_text() == (
        "### MAE per year\n\n| split | year | n |\n|---|---|---|\n| test | 2026 | 42 |\n\n"
    )
