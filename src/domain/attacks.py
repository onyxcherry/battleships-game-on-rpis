from pydantic.dataclasses import dataclass
import enum
from pydantic import ConfigDict, BeforeValidator, PlainSerializer

from domain.field import Field
from pydantic import Field as PydField
from typing import Literal, Annotated, Any


dataclass_config = ConfigDict(
    populate_by_name=True, arbitrary_types_allowed=True, use_enum_values=True
)


class AttackResultStatus(str, enum.Enum):
    ShotDown = "ShotDown"
    Shot = "Shot"
    AlreadyShot = "AlreadyShot"
    Missed = "Missed"


UnknownStatus = Literal["Unknown"]


def bv(v: Any) -> Field:
    if isinstance(v, Field):
        return v
    return Field(v)


def ps(v: Any) -> str:
    if isinstance(v, Field):
        return v.name
    return v


BattleshipFieldDeser = Annotated[Field, BeforeValidator(bv), PlainSerializer(ps)]


@dataclass(frozen=True, config=dataclass_config)
class AttackResult:
    field: BattleshipFieldDeser
    status: AttackResultStatus
    type_: Literal["AttackResult"] = PydField(
        default="AttackResult", init=False, repr=False
    )


@dataclass(frozen=True, config=dataclass_config)
class AttackRequest:
    field: BattleshipFieldDeser
    type_: Literal["AttackRequest"] = PydField(
        default="AttackRequest", init=False, repr=False
    )
