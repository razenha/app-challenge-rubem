import logging

from huey import RedisHuey

from app.config import REDIS_URL, validate_required_config
from app.logging_setup import init_logging
from app.starkbank_setup import init_starkbank

init_logging()

huey = RedisHuey("starkbank-challenge", url=REDIS_URL)

# Import tasks so the @huey.task decorators register them in the TaskRegistry.
# Required for the huey_consumer to know about all tasks.
import app.jobs  # noqa: E402, F401


@huey.on_startup()
def _worker_startup():
    validate_required_config()
    # Re-apply logging config so it wins over huey_consumer's own setup.
    init_logging()
    init_starkbank()
    logger = logging.getLogger(__name__)
    logger.info(
        "Huey tasks registered: %s",
        sorted(huey._registry._registry.keys()),
    )
