from dataclasses import dataclass
import logging
import sys
from typing import Final, Literal


FORMATTER = logging.Formatter(
    "%(asctime)s %(levelname)s %(module)s %(funcName)s: %(message)s"
)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    logger.addHandler(console_handler)

    logger.propagate = False

    level = logging.getLevelNamesMapping().get(CONFIG.logging_level)
    if level is None:
        logger.setLevel(logging.INFO)
        logger.info("Logging level set to INFO as provided level not found!")
    else:
        logger.setLevel(level)

    return logger


@dataclass(frozen=True)
class Config:
    mode: Literal["terminal", "pygame", "rgbled"]
    logging_level: Literal["DEBUG", "INFO", "WARNING"]


CONFIG: Final = Config(mode="pygame", logging_level="INFO")
