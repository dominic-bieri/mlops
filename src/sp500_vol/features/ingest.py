import logging
from datetime import date, timedelta

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.features.fred_client import FredClient
from sp500_vol.features.tiingo_client import TiingoClient

logger = logging.getLogger(__name__)

# first SPY trading day, used when a table is still empty
BACKFILL_START = date(1993, 1, 29)

# reload a few days before the latest stored date, so values FRED publishes late are picked up
OVERLAP_DAYS = 7


def get_start(latest: date | None) -> date:
    if latest is None:
        return BACKFILL_START
    return latest - timedelta(days=OVERLAP_DAYS)


def main() -> None:
    fred = FredClient()
    tiingo = TiingoClient()
    bq = BigQueryClient()
    end = date.today()

    latest_dates = bq.get_latest_dates(["vix", "sp500"])
    vix_start = get_start(latest_dates["vix"])
    sp500_start = get_start(latest_dates["sp500"])

    # fetch both first, so a failed fetch from one source writes nothing.
    # if the second upsert fails, vix is ahead of sp500 until the next run;
    # this fixes itself because each table gets its own start date
    vix = fred.fetch_vix(vix_start, end)
    sp500 = tiingo.fetch_spy(sp500_start, end)

    bq.upsert(vix, "vix")
    logger.info("vix: %d rows since %s", len(vix), vix_start)

    bq.upsert(sp500, "sp500")
    logger.info("sp500: %d rows since %s", len(sp500), sp500_start)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
