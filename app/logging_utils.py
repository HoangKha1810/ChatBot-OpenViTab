from __future__ import annotations

import logging
import sys


LOGGER_NAME = "tableqa"
_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [TableQA] %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)

    _CONFIGURED = True


def log_step(request_id: str, stage: str, message: str) -> None:
    configure_logging()
    logging.getLogger(LOGGER_NAME).info("[%s] %-16s %s", request_id, stage, message)
