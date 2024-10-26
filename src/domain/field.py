from dataclasses import dataclass
from typing import TypeVar
import enum

CoordinateX = TypeVar("CoordinateX", bound=str)
CoordinateY = TypeVar("CoordinateY", bound=str)


@dataclass(frozen=True)
class Field:
    x: CoordinateX
    y: CoordinateY

    @property
    def name(self) -> str:
        return (self.x + self.y).upper()


class AttackResult(enum.StrEnum):
    ShotDown = "ShotDown"
    Shot = "Shot"
    Missed = "Missed"


@dataclass(frozen=True)
class AttackedField:
    field: Field
    result: AttackResult
