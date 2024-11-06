from domain.boards import LaunchedShipCollidesError, ShipsBoard, get_all_ship_fields
from domain.field import Field
from domain.ships import MastedShips, MastedShipsCounts, Ship
from pydantic import ValidationError
import pytest


def tests_merging_fields_into_ships():
    ships_fields = {
        Field("A3"),
        Field("A4"),
        Field("E8"),
        Field("C7"),
        Field("C8"),
        Field("D7"),
    }
    ships = ShipsBoard.build_ships_from_fields(ships_fields)
    expected_ships = {
        Ship({Field("A3"), Field("A4")}),
        Ship({Field("C7"), Field("D7"), Field("C8")}),
        Ship({Field("E8")}),
    }
    assert ships == expected_ships


def test_getting_all_ship_fields_when_one_given():
    fields = {
        Field("A3"),
        Field("A4"),
        Field("E5"),
        Field("F5"),
        Field("G5"),
        Field("G6"),
        Field("G7"),
        Field("D9"),
        Field("D10"),
    }
    assert get_all_ship_fields(fields, Field("G5")) == {
        Field("G7"),
        Field("F5"),
        Field("G5"),
        Field("G6"),
        Field("E5"),
    }


def tests_adding_not_colliding_ships():
    ships_board = ShipsBoard()
    ship1 = Ship({Field("A3"), Field("A4")})
    ship2 = Ship({Field("D8"), Field("C8")})
    ships_board.add_ship(ship1)
    ships_board.add_ship(ship2)


def tests_raising_exception_when_adding_colliding_ships():
    ships_board = ShipsBoard()
    ship1 = Ship({Field("A3"), Field("A4")})
    ship2 = Ship({Field("B5"), Field("C5")})
    ships_board.add_ship(ship1)
    with pytest.raises(LaunchedShipCollidesError):
        ships_board.add_ship(ship2)


def tests_masted_ships_when_counts_matches():
    counts = MastedShipsCounts(single=4, two=3, three=2, four=1)
    MastedShips(
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


def test_raising_exception_when_masted_ships_counts_do_not_follow_rules():
    counts = MastedShipsCounts(single=4, two=3, three=2, four=1)

    with pytest.raises(ValidationError):
        MastedShips(
            counts=counts,
            single={
                Ship({Field("A1")}),
                Ship({Field("J6")}),
                Ship({Field("H1")}),
            },
            two={
                Ship({Field("A3"), Field("A4")}),
                Ship({Field("B9"), Field("C9")}),
            },
            three={
                Ship({Field("J1"), Field("J2"), Field("J3")}),
                Ship({Field("H8"), Field("I8"), Field("J8")}),
            },
            four=set({Ship({Field("C1"), Field("D1"), Field("E1"), Field("F1")})}),
        )
