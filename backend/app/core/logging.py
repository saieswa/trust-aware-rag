"""
Centralized logging setup.

We use loguru instead of the standard `logging` module because it gives us
structured, readable output with almost no boilerplate, and it plays well
with async FastAPI code. `configure_logging()` is called once at app
startup (see app/main.py), and every other module just does:

    from loguru import logger
    logger.info("something happened")

and it automatically uses the configuration set here.
"""

import sys

from loguru import logger

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()

    logger.remove()  # remove loguru's default handler so we control the format

    if settings.LOG_JSON:
        # Structured JSON logs — useful in production when logs are shipped
        # to a log aggregator (e.g. ELK, Datadog, CloudWatch).
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL,
            serialize=True,
            backtrace=False,
            diagnose=False,
        )
    else:
        # Human-readable colored logs — nicer for local development.
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
            backtrace=settings.APP_DEBUG,
            diagnose=settings.APP_DEBUG,
        )

    logger.info(
        f"Logging configured | level={settings.LOG_LEVEL} "
        f"json={settings.LOG_JSON} env={settings.APP_ENV}"
    )
