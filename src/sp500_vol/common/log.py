import logging
import os

logger = logging.getLogger(__name__)


def github_summary(title: str, lines: list[str]) -> None:
    text = f"### {title}\n\n" + "".join(f"- {line}\n" for line in lines)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path is None:
        logger.info("%s", text)
        return
    with open(path, "a") as file:
        file.write(text + "\n")


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
