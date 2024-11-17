from domain.field import Field
from domain.ships import (
    MastedShips,
    Ship,
    ShipBiggerThanAllowedError,
    ShipCountNotConformingError,
    ships_of_standard_count,
)
from pydantic import ValidationError
import pytest
from config import MastedShipsCounts


def tests_masted_ships_of_standard_count():
    _ = ships_of_standard_count()


def tests_creating_masted_ships_from_set_of_compatible_ships():
    counts = MastedShipsCounts(single=4, two=3, three=2, four=1)
    ships = {
        Ship({Field("A1")}),
        Ship({Field("H10")}),
        Ship({Field("J6")}),
        Ship({Field("H1")}),
        Ship({Field("A3"), Field("A4")}),
        Ship({Field("B9"), Field("C9")}),
        Ship({Field("E10"), Field("F10")}),
        Ship({Field("J1"), Field("J2"), Field("J3")}),
        Ship({Field("H8"), Field("I8"), Field("J8")}),
        Ship({Field("C1"), Field("D1"), Field("E1"), Field("F1")}),
    }
    result = MastedShips.from_set(ships, counts)
    assert result == MastedShips(
        counts=MastedShipsCounts(single=4, two=3, three=2, four=1),
        single={
            Ship({Field("J6")}),
            Ship({Field("H10")}),
            Ship({Field("H1")}),
            Ship({Field("A1")}),
        },
        two={
            Ship({Field("C9"), Field("B9")}),
            Ship({Field("E10"), Field("F10")}),
            Ship({Field("A3"), Field("A4")}),
        },
        three={
            Ship({Field("I8"), Field("J8"), Field("H8")}),
            Ship({Field("J3"), Field("J2"), Field("J1")}),
        },
        four={Ship({Field("E1"), Field("D1"), Field("C1"), Field("F1")})},
    )


def tests_creating_masted_ships_fails_due_to_ship_bigger_than_allowed():
    counts = MastedShipsCounts(single=1, two=1, three=1, four=0)
    five_masts_ship = Ship(
        {Field("C1"), Field("D1"), Field("E1"), Field("F1"), Field("G1")}
    )
    ships = {
        Ship({Field("H1")}),
        Ship({Field("E10"), Field("F10")}),
        Ship({Field("H8"), Field("I8"), Field("J8")}),
        five_masts_ship,
    }
    with pytest.raises(ShipBiggerThanAllowedError) as ex:
        _ = MastedShips.from_set(ships, counts)
    assert ex.value.ship == five_masts_ship


def tests_creating_masted_ships_fails_due_to_more_than_expected_ships_of_two_masts():
    counts = MastedShipsCounts(single=1, two=1, three=1, four=0)
    ships = {
        Ship({Field("H1")}),
        Ship({Field("A1"), Field("A2")}),
        Ship({Field("E10"), Field("F10")}),
        Ship({Field("H8"), Field("I8"), Field("J8")}),
    }
    with pytest.raises(ShipCountNotConformingError) as ex:
        _ = MastedShips.from_set(ships, counts)
    assert ex.value.ships == set(
        [Ship({Field("A1"), Field("A2")}), Ship({Field("E10"), Field("F10")})]
    )


def tests_direct_creating_masted_ships_fails_due_to_improper_count_of_ships():
    counts = MastedShipsCounts(single=1, two=1, three=1, four=0)
    with pytest.raises(ValidationError):
        _ = MastedShips(
            counts=counts,
            single={Ship({Field("H1")})},
            two={Ship({Field("A1"), Field("A2")}), Ship({Field("E10"), Field("F10")})},
            three={Ship({Field("H8"), Field("I8"), Field("J8")})},
            four=set(),
        )
