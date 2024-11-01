from abc import ABC, abstractmethod
from typing import Literal
from pydantic.dataclasses import dataclass
from domain.attacks import AttackRequest, AttackResult
import json
from pydantic import UUID4, Field as PydField


from pydantic import TypeAdapter, RootModel, ConfigDict

dataclass_config = ConfigDict(populate_by_name=True)


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
    opponent_connected: bool
    what: Literal["ClientInfo"] = PydField(default="ClientInfo", init=False, repr=False)

    def serialize(self) -> dict:
        return RootModel[ClientInfo](self).model_dump(by_alias=True, mode="json")

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


def parse_message(data: dict) -> GameMessage:
    message = TypeAdapter(GameMessage).validate_python(data)
    return message


def serialize_message(message: GameMessage) -> str:
    return RootModel[type(message)](message).model_dump(by_alias=True)
