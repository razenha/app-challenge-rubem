import starkbank

from app.config import (
    STARKBANK_ENVIRONMENT,
    STARKBANK_PROJECT_ID,
    get_private_key,
)


def init_starkbank():
    starkbank.user = starkbank.Project(
        environment=STARKBANK_ENVIRONMENT,
        id=STARKBANK_PROJECT_ID,
        private_key=get_private_key(),
    )
