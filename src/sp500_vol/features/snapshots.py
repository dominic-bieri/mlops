import logging
from datetime import datetime, timedelta

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.registry import ModelRegistry
from sp500_vol.common.schema import SNAPSHOT_PREFIX

logger = logging.getLogger(__name__)

MAX_SNAPSHOT_AGE = timedelta(days=60)


def get_snapshots_to_delete(
    snapshots: dict[str, datetime], used: set[str], now: datetime
) -> list[str]:
    if not snapshots:
        return []
    newest = max(snapshots)
    to_delete = []
    for name, created in sorted(snapshots.items()):
        if name == newest or name in used:
            continue
        if now - created > MAX_SNAPSHOT_AGE:
            to_delete.append(name)
    return to_delete


def delete_old_snapshots(bq: BigQueryClient, now: datetime) -> list[str]:
    snapshots = bq.get_snapshots(SNAPSHOT_PREFIX)
    used = ModelRegistry().get_used_snapshots()
    to_delete = get_snapshots_to_delete(snapshots, used, now)
    for name in to_delete:
        bq.delete_snapshot(name)
        logger.info("deleted snapshot %s", name)
    return to_delete
