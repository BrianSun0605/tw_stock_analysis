import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import LOG_DIR

_loggers = {}


def get_logger(name: str = "twstock") -> logging.Logger:
    if name in _loggers:
        return _loggers[name]
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(console)
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            file_handler = RotatingFileHandler(
                os.path.join(LOG_DIR, "app.log"),
                maxBytes=5 * 1024 * 1024,
                backupCount=4,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            pass
    _loggers[name] = logger
    return logger
