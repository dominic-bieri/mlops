from datetime import UTC, datetime, timedelta

import pytest

from sp500_vol.features import build
from sp500_vol.features.snapshots import MAX_SNAPSHOT_AGE, get_snapshots_to_delete

NOW = datetime(2026, 11, 21, 15, tzinfo=UTC)
OLD = NOW - MAX_SNAPSHOT_AGE - timedelta(days=1)
RECENT = NOW - timedelta(days=1)


def test_old_unused_snapshot_is_deleted() -> None:
    snapshots = {"features_20260901_150000": OLD, "features_20261120_150000": RECENT}

    assert get_snapshots_to_delete(snapshots, set(), NOW) == ["features_20260901_150000"]


def test_snapshot_of_a_model_version_is_kept() -> None:
    snapshots = {"features_20260901_150000": OLD, "features_20261120_150000": RECENT}

    used = {"features_20260901_150000"}

    assert get_snapshots_to_delete(snapshots, used, NOW) == []


def test_newest_snapshot_is_kept_even_if_old() -> None:
    snapshots = {"features_20260801_150000": OLD, "features_20260901_150000": OLD}

    assert get_snapshots_to_delete(snapshots, set(), NOW) == ["features_20260801_150000"]


def test_no_snapshots_nothing_to_delete() -> None:
    assert get_snapshots_to_delete({}, set(), NOW) == []


def test_failed_cleanup_only_warns(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def fail(*args: object) -> list[str]:
        raise PermissionError("no access to the registry")

    monkeypatch.setattr(build, "delete_old_snapshots", fail)

    deleted = build.clean_up_snapshots(None)

    assert deleted == []
    out = capsys.readouterr().out
    assert out.startswith("::warning title=Features: snapshot cleanup failed::PermissionError")
