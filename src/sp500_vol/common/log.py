import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)


def github_summary(title: str, lines: list[str]) -> None:
    write_summary(f"### {title}\n\n" + "".join(f"- {line}\n" for line in lines))


def github_table(title: str, df: pd.DataFrame) -> None:
    header = "| " + " | ".join(df.columns) + " |\n"
    divider = "|" + "---|" * len(df.columns) + "\n"
    rows = ""
    for row in df.itertuples(index=False):
        rows += "| " + " | ".join(str(value) for value in row) + " |\n"
    write_summary(f"### {title}\n\n" + header + divider + rows)


def write_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path is None:
        logger.info("%s", text)
        return
    with open(path, "a") as file:
        file.write(text + "\n")


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
