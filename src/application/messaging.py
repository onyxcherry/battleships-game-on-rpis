from pydantic.dataclasses import dataclass
import uuid
from domain.attacks import AttackRequest, AttackResult

from pydantic import Field as PydField


from pydantic import TypeAdapter, RootModel, ConfigDict

dataclass_config = ConfigDict(populate_by_name=True)


@dataclass(frozen=True, config=dataclass_config)
class Message:
    uniqid: uuid.UUID
    # TODO: rename to `type`
    data: AttackRequest | AttackResult = PydField(discriminator="type_")


def parse_message(data: dict) -> Message:
    message = TypeAdapter(Message).validate_python(data)
    return message


def serialize_message(message: Message) -> str:
    return RootModel[type(message)](message).model_dump(by_alias=True)
