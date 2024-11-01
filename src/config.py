import logging
import sys


FORMATTER = logging.Formatter(
    "%(asctime)s.%(msecs)03d %(levelname)s %(module)s - " "%(funcName)s: %(message)s"
)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    logger.addHandler(console_handler)

    logger.propagate = False

    return logger
