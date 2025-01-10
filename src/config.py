import logging
import sys
from typing import Final, Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


FORMATTER = logging.Formatter(
    "%(asctime)s %(levelname)s %(module)s %(funcName)s: %(message)s"
)

dataclass_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


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


@dataclass(frozen=True, config=dataclass_config)
class MastedShipsCounts:
    single: int
    two: int
    three: int
    four: int


@dataclass(frozen=True)
class Config:
    server_host: str
    server_port: int
    mode: Literal["terminal", "pygame", "rgbled"]
    logging_level: Literal["DEBUG", "INFO", "WARNING"]
    masted_ships_counts = MastedShipsCounts(single=1, two=1, three=1, four=0)
    board_size = 10
    conn_ping_interval = 20
    conn_ping_timeout = 5


@dataclass(frozen=True)
class ClientConfig:
    game_ended_state_show_seconds: float
    min_duration_to_show_animation_in_seconds: float


CONFIG: Final = Config(
    server_host="10.42.0.1", server_port=4200, mode="rgbled", logging_level="INFO"
)

CLIENT_CONFIG: Final = ClientConfig(
    game_ended_state_show_seconds=5.0, min_duration_to_show_animation_in_seconds=1.0
)
