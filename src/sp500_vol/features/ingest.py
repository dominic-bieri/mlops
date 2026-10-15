import logging
from datetime import date, timedelta

import pandas as pd

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.features.fred_client import FredClient
from sp500_vol.features.tiingo_client import TiingoClient

logger = logging.getLogger(__name__)

BACKFILL_START = date(1993, 1, 29)

# catches late FRED values
OVERLAP_DAYS = 7


def get_start(latest: date | None) -> date:
    if latest is None:
        return BACKFILL_START
    return latest - timedelta(days=OVERLAP_DAYS)


def only_new(df: pd.DataFrame, existing: set[date], loaded_at: pd.Timestamp) -> pd.DataFrame:
    new = df[~df["date"].isin(existing)].copy()
    new["loaded_at"] = loaded_at
    return new


def main() -> None:
    fred = FredClient()
    tiingo = TiingoClient()
    bq = BigQueryClient()
    end = date.today()
    loaded_at = pd.Timestamp.now(tz="UTC")

    vix_dates = bq.get_dates("vix")
    sp500_dates = bq.get_dates("sp500")
    vix_start = get_start(max(vix_dates, default=None))
    sp500_start = get_start(max(sp500_dates, default=None))

    vix = fred.fetch_vix(vix_start, end)
    sp500 = tiingo.fetch_spy(sp500_start, end)

    new_vix = only_new(vix, vix_dates, loaded_at)
    bq.append(new_vix, "vix")
    logger.info("vix: %d new rows since %s", len(new_vix), vix_start)

    new_sp500 = only_new(sp500, sp500_dates, loaded_at)
    bq.append(new_sp500, "sp500")
    logger.info("sp500: %d new rows since %s", len(new_sp500), sp500_start)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
