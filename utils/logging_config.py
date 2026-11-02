"""
Central logging setup for Zephyr.

Importing this module configures the "zephyr" logger once (idempotent), so
every module just does:

    from utils.logging_config import get_logger
    log = get_logger("dm")

INFO  -> things a human wants to read (DM sent, reply sent, skipped, failed)
DEBUG -> noisy detail (comments that matched no rule, dedupe skips, DB log saves)
        only shown when DEBUG=true in the environment.
"""
import logging
import sys

from settings import DEBUG

_ROOT = "zephyr"


def _configure() -> logging.Logger:
    logger = logging.getLogger(_ROOT)
    if logger.handlers:  # already configured (module imported twice / reload)
        return logger

    # Emoji need UTF-8; make sure a weird console encoding can't crash logging.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s │ %(levelname)-7s │ %(name)-14s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    logger.propagate = False  # don't double-print through uvicorn's root handlers
    return logger


_configure()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{_ROOT}.{name}")