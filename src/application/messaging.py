from abc import ABC, abstractmethod
import enum
from typing import Literal, Optional
from domain.ships import MastedShipsCounts
from pydantic.dataclasses import dataclass
from domain.attacks import AttackRequest, AttackResult
import json
from pydantic import UUID4, Field as PydField


from pydantic import TypeAdapter, RootModel, ConfigDict

dataclass_config = ConfigDict(populate_by_name=True)

type GameMessageOrInfo = GameMessage | GameInfo


class GameStatus(enum.StrEnum):
    WaitingToStart = "WaitingToStart"
    Started = "Started"
    Ended = "Ended"
    InBadState = "InBadState"


class Serializable(ABC):
    @abstractmethod
    def serialize(self) -> dict:
        pass

    @abstractmethod
    def stringify(self) -> str:
        pass


@dataclass(frozen=True, config=dataclass_config)
class ClientInfo(Serializable):
    uniqid: UUID4
    connected: bool
    ships_placed: bool
    ready: bool
    all_ships_wrecked: bool
    what: Literal["ClientInfo"] = PydField(default="ClientInfo", init=False, repr=False)

    def serialize(self) -> dict:
        return RootModel[ClientInfo](self).model_dump(by_alias=True, mode="json")

    def stringify(self) -> str:
        return json.dumps(self.serialize())


@dataclass(frozen=True, config=dataclass_config)
class ExtraInfo:
    you_start_first: Optional[bool] = None
    you_won: Optional[bool] = None
    error: Optional[str] = None


@dataclass(frozen=True, config=dataclass_config)
class GameInfo(Serializable):
    uniqid: UUID4
    status: GameStatus
    opponent: Optional[ClientInfo]
    masted_ships: MastedShipsCounts
    board_size: int
    extra: Optional[ExtraInfo] = None
    what: Literal["GameInfo"] = PydField(default="GameInfo", init=False, repr=False)

    def serialize(self) -> dict:
        return RootModel[GameInfo](self).model_dump(by_alias=True, mode="json")

    def stringify(self) -> str:
        return json.dumps(self.serialize())


@dataclass(frozen=True, config=dataclass_config)
class GameMessage(Serializable):
    uniqid: UUID4
    # TODO: rename to `type`
    data: AttackRequest | AttackResult = PydField(discriminator="type_")
    what: Literal["GameMessage"] = PydField(
        default="GameMessage", init=False, repr=False
    )

    def serialize(self) -> dict:
        return RootModel[GameMessage](self).model_dump(by_alias=True, mode="json")

    def stringify(self) -> str:
        return json.dumps(self.serialize())


def parse_client_info(data: dict) -> ClientInfo:
    message = TypeAdapter(ClientInfo).validate_python(data)
    return message


def parse_game_info(data: dict) -> GameInfo:
    message = TypeAdapter(GameInfo).validate_python(data)
    return message


def parse_game_message(data: dict) -> GameMessage:
    message = TypeAdapter(GameMessage).validate_python(data)
    return message


def parse_game_message_or_info(data: dict) -> GameMessageOrInfo:
    message = TypeAdapter(GameMessageOrInfo).validate_python(data)
    return message


def serialize_message(message: GameMessage) -> str:
    return RootModel[type(message)](message).model_dump(by_alias=True)
