import logging

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.registry import ModelRegistry
from sp500_vol.common.schema import SNAPSHOT_PREFIX

logger = logging.getLogger(__name__)


# older features can be built again from the append-only raw tables (ADR 1)
def get_snapshots_to_delete(snapshots: list[str], used: set[str]) -> list[str]:
    if not snapshots:
        return []
    newest = max(snapshots)
    to_delete = []
    for name in sorted(snapshots):
        if name != newest and name not in used:
            to_delete.append(name)
    return to_delete


def delete_unused_snapshots(bq: BigQueryClient) -> list[str]:
    snapshots = bq.get_snapshots(SNAPSHOT_PREFIX)
    used = ModelRegistry().get_used_snapshots()
    to_delete = get_snapshots_to_delete(snapshots, used)
    for name in to_delete:
        bq.delete_snapshot(name)
        logger.info("deleted snapshot %s", name)
    return to_delete
