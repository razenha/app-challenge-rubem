import logging
import sys

from app.config import DEBUG, LOG_LEVEL


def init_logging():
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )

    if DEBUG:
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("starkbank").setLevel(logging.DEBUG)
        logging.getLogger("starkcore").setLevel(logging.DEBUG)
    else:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
