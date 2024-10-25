import enum
from domain.field import Field, AttackResult
from typing import Annotated, Final


class ShipStatus(enum.StrEnum):
    Wrecked = "Wrecked"
    ShotButFloats = "ShotButFloats"
    FullyOperational = "ShotButFloats"


class Ship:
    def __init__(self, fields: list[Field]) -> None:
        self._fields: Final = fields
        self._parts_floating = fields
        self._parts_wrecked: list[Field] = []

    @property
    def original_masts_count(self) -> int:
        return len(self._fields)

    @property
    def fields(self) -> list[Field]:
        return self._fields

    @property
    def waving_masts_count(self) -> int:
        return len(self._parts_floating)

    @property
    def status(self) -> ShipStatus:
        if self.waving_masts_count == 0:
            return ShipStatus.Wrecked
        elif self.waving_masts_count < self.original_masts_count:
            return ShipStatus.ShotButFloats
        return ShipStatus.FullyOperational

    def attack(self, field: Field) -> AttackResult:
        if field not in self._parts_floating:
            return AttackResult.Missed

        self._parts_floating.remove(field)
        self._parts_wrecked.append(field)
        if self.status == ShipStatus.ShotButFloats:
            return AttackResult.Shot
        elif self.status == ShipStatus.Wrecked:
            return AttackResult.ShotDown
        else:
            raise RuntimeError(f"Bad ship state: {self.status}")


class MastedShips:
    single: Annotated[list[Ship], 4]
    two: Annotated[list[Ship], 3]
    three: Annotated[list[Ship], 2]
    four: Annotated[list[Ship], 1]
