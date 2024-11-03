import dataclasses
import enum
from domain.attacks import AttackResultStatus
from domain.field import Field
from typing import Final, Self
from pydantic.dataclasses import dataclass

from pydantic import ConfigDict


import copy

dataclass_config = ConfigDict(populate_by_name=True)


class ShipStatus(enum.StrEnum):
    Wrecked = "Wrecked"
    ShotButFloats = "ShotButFloats"
    FullyOperational = "ShotButFloats"


class Ship:
    def __init__(self, fields: set[Field]) -> None:
        if not self.can_be_built_from_fields(fields):
            raise RuntimeError("Invalid fields for the ship")
        self._fields: Final = fields
        self._parts_floating = copy.deepcopy(fields)
        self._parts_wrecked: set[Field] = set()

    @property
    def original_masts_count(self) -> int:
        return len(self._fields)

    @property
    def fields(self) -> set[Field]:
        return self._fields

    @property
    def wrecked_masts(self) -> set[Field]:
        return self._parts_wrecked

    @property
    def waving_masts(self) -> set[Field]:
        return self._parts_floating

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

    @property
    def fields_with_coastal_zone(self) -> set[Field]:
        return self._fields.union(self._infer_coastal_zone())

    @property
    def _properties(self) -> tuple[frozenset, frozenset, frozenset]:
        return (
            frozenset(self.fields),
            frozenset(self.waving_masts),
            frozenset(self.wrecked_masts),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ship):
            return False
        return self._properties == other._properties

    def __hash__(self) -> int:
        return hash(self._properties)

    def _infer_coastal_zone(self) -> set[Field]:
        adjacency_vectors = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]
        coastal_zone: set[Field] = set()
        for field in self._fields:
            adjacent_fields_list = list(
                filter(
                    lambda field: field is not None,
                    [field.moved_by(*vector) for vector in adjacency_vectors],
                )
            )
            for adjacent_field in adjacent_fields_list:
                assert adjacent_field is not None
                if adjacent_field not in self._fields:
                    coastal_zone.add(adjacent_field)
        return coastal_zone

    def attack(self, field: Field) -> AttackResultStatus:
        if field not in self._parts_floating:
            if field not in self._parts_wrecked:
                return AttackResultStatus.Missed
            return AttackResultStatus.AlreadyShot

        self._parts_floating.remove(field)
        self._parts_wrecked.add(field)
        if self.status == ShipStatus.ShotButFloats:
            return AttackResultStatus.Shot
        elif self.status == ShipStatus.Wrecked:
            return AttackResultStatus.ShotDown
        else:
            raise RuntimeError(f"Bad ship state: {self.status}")

    @staticmethod
    def can_be_built_from_fields(fields: set[Field]) -> bool:
        if 1 <= len(fields) <= 4:
            return True
        return False

    @classmethod
    def from_parts(cls, *, wrecked: set[Field], waving: set[Field]) -> Self:
        ship = cls(wrecked.union(waving))
        ship._parts_wrecked = wrecked
        ship._parts_floating = waving
        return ship

    def __str__(self) -> str:
        waving_masts_codes = [field.name for field in self.waving_masts]
        wrecked_masts_codes = [field.name for field in self.wrecked_masts]
        return f"Ship<{len(self.fields)}>(🏳️ {",".join(waving_masts_codes) or "empty"}|💀 {",".join(wrecked_masts_codes) or "empty"})"

    def __repr__(self) -> str:
        return f"Ship({self.fields!r})"


@dataclasses.dataclass(frozen=True)
class MastedShips:
    single: set[Ship]
    two: set[Ship]
    three: set[Ship]
    four: set[Ship]


@dataclass(frozen=True, config=dataclass_config)
class MastedShipsCounts:
    single: int
    two: int
    three: int
    four: int
