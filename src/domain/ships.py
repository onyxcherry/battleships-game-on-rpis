import enum
from domain.attacks import AttackResultStatus
from domain.field import Field
from typing import Annotated, Final, Self
import copy


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
        all_fields: set[Field] = set()
        all_fields.add(self._fields)
        all_fields.add(self._infer_coastal_zone())
        return all_fields

    @property
    def _properties(self) -> tuple[set, set, set]:
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
        coastal_zone: set[Field] = []
        for field in self._fields:
            for adjacent_field in [
                field.moved_by(*vector) for vector in adjacency_vectors
            ]:
                if adjacent_field not in self._fields:
                    coastal_zone.add(adjacent_field)
        return coastal_zone

    def attack(self, field: Field) -> AttackResultStatus:
        if field not in self._parts_floating:
            if field not in self._parts_wrecked:
                return AttackResultStatus.Missed
            return AttackResultStatus.AlreadyShot

        self._parts_floating.remove(field)
        self._parts_wrecked.append(field)
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
        all_fields = [*wrecked, *waving]
        ship = cls(all_fields)
        ship._parts_wrecked = wrecked
        ship._parts_floating = waving
        return ship

    def __str__(self) -> str:
        waving_masts_codes = [field.name for field in self.waving_masts]
        wrecked_masts_codes = [field.name for field in self.wrecked_masts]
        return f"Ship<{len(self.fields)}>(🏳️ {",".join(waving_masts_codes) or "empty"}|💀 {",".join(wrecked_masts_codes) or "empty"})"

    def __repr__(self) -> str:
        return f"Ship({self.fields!r})"


class MastedShips:
    single: Annotated[set[Ship], 4]
    two: Annotated[set[Ship], 3]
    three: Annotated[set[Ship], 2]
    four: Annotated[set[Ship], 1]
