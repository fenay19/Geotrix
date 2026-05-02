import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configures the application-level logger and returns it.
    Call once from main.py at startup.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logger = logging.getLogger("geotrade")
    logger.info("GeoTrade AI logging initialized at level %s", level)
    return logger


# Module-level logger — import this in other modules instead of calling setup_logging()
logger = logging.getLogger("geotrade")
