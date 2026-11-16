import logging


# shown on the run page, readable without a GitHub login
def github_notice(title: str, parts: list[str]) -> None:
    print(f"::notice title={title}::{' · '.join(parts)}")


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
