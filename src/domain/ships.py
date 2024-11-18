import enum
from config import MastedShipsCounts
from domain.attacks import AttackResultStatus
from domain.field import Field
from typing import Final, Self
from pydantic.dataclasses import dataclass
import copy

from pydantic import ConfigDict, model_validator


dataclass_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class ShipStatus(enum.StrEnum):
    Wrecked = "Wrecked"
    ShotButFloats = "ShotButFloats"
    FullyOperational = "ShotButFloats"


class Ship:
    def __init__(self, fields: set[Field]) -> None:
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

    def __lt__(self, other: Self) -> bool:
        return (self.original_masts_count, sorted(self.fields)) < (
            other.original_masts_count,
            sorted(other.fields),
        )

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

    @classmethod
    def from_parts(cls, *, wrecked: set[Field], waving: set[Field]) -> Self:
        ship = cls(wrecked.union(waving))
        ship._parts_wrecked = wrecked
        ship._parts_floating = waving
        return ship

    def __str__(self) -> str:
        waving_masts_codes = [field.name for field in self.waving_masts]
        wrecked_masts_codes = [field.name for field in self.wrecked_masts]
        waving = ",".join(waving_masts_codes) or "empty"
        wrecked = ",".join(wrecked_masts_codes) or "empty"
        return f"Ship<{len(self.fields)}>(🏳️ {waving}|💀 {wrecked})"

    def __repr__(self) -> str:
        return f"Ship({self.fields!r})"


class ShipBiggerThanAllowedError(ValueError):
    def __init__(self, msg, ship: Ship) -> None:
        self.ship = ship


class ShipCountNotConformingError(ValueError):
    def __init__(self, msg, ships: set[Ship]) -> None:
        self.ships = ships


@dataclass(frozen=True, config=dataclass_config)
class MastedShips:
    counts: MastedShipsCounts
    single: set[Ship]
    two: set[Ship]
    three: set[Ship]
    four: set[Ship]

    @model_validator(mode="after")
    def verify_counts(self) -> Self:
        ships_of_mast_count = {1: self.single, 2: self.two, 3: self.three, 4: self.four}
        self.verify_conformity_of_counts(ships_of_mast_count, self.counts)
        return self

    @classmethod
    def verify_conformity_of_counts(
        cls, ships_of_mast_count: dict[int, set[Ship]], counts: MastedShipsCounts
    ) -> None:
        counts_mapping = {1: "single", 2: "two", 3: "three", 4: "four"}
        for masts_count, ships in ships_of_mast_count.items():
            expected_count = getattr(counts, counts_mapping[masts_count])
            if len(ships) != expected_count:
                raise ShipCountNotConformingError(
                    f"Improper count (provided {len(ships)} ships) of single masts"
                    + f"(expected {expected_count})",
                    ships=ships,
                )

    @classmethod
    def from_set(cls, ships: set[Ship], counts: MastedShipsCounts) -> Self:
        ships_of_mast_count = {1: set(), 2: set(), 3: set(), 4: set()}
        for ship in ships:
            if ship.original_masts_count not in ships_of_mast_count:
                raise ShipBiggerThanAllowedError(
                    f"Ship {ship} have {ship.original_masts_count} masts whereas"
                    + " only 4 masts are allowed at maximum",
                    ship=ship,
                )
            ships_of_mast_count[ship.original_masts_count].add(ship)
        cls.verify_conformity_of_counts(ships_of_mast_count, counts)
        return cls(
            counts=counts,
            single=ships_of_mast_count[1],
            two=ships_of_mast_count[2],
            three=ships_of_mast_count[3],
            four=ships_of_mast_count[4],
        )


def ships_of_standard_count():
    counts = MastedShipsCounts(single=4, two=3, three=2, four=1)
    ships = MastedShips(
        counts=counts,
        single={
            Ship({Field("A1")}),
            Ship({Field("H10")}),
            Ship({Field("J6")}),
            Ship({Field("H1")}),
        },
        two={
            Ship({Field("A3"), Field("A4")}),
            Ship({Field("B9"), Field("C9")}),
            Ship({Field("E10"), Field("F10")}),
        },
        three={
            Ship({Field("J1"), Field("J2"), Field("J3")}),
            Ship({Field("H8"), Field("I8"), Field("J8")}),
        },
        four=set({Ship({Field("C1"), Field("D1"), Field("E1"), Field("F1")})}),
    )
    return ships
