"""Load all artifacts at startup. Zero disk reads at request time."""

import logging

from app.config import LAYER2_ARTIFACTS, LAYER3_ARTIFACTS

logger = logging.getLogger(__name__)


def startup(app=None):
    """Load Layer 2 and Layer 3 artifacts. Call once per worker at process start."""
    logger.info("Loading Layer 2 calibration tables from %s", LAYER2_ARTIFACTS)
    from layers import layer2
    layer2.load_calibration_tables(str(LAYER2_ARTIFACTS))

    logger.info("Loading Layer 3 embeddings from %s", LAYER3_ARTIFACTS)
    from layers import layer3
    layer3.load_embeddings(str(LAYER3_ARTIFACTS))

    from app.cache import warmup_cache
    warmup_cache()

    if app is not None:
        app.state.ready = True
    logger.info("Startup complete; ready to serve requests.")
