from sp500_vol.common.config import setup_logging
from sp500_vol.features import build, ingest


def main() -> None:
    ingest.main()
    build.main()


if __name__ == "__main__":
    setup_logging()
    main()
