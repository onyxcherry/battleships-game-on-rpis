from domain.boards import LaunchedShipCollidesError, ShipsBoard, get_all_ship_fields
from domain.field import Field
from domain.ships import Ship
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
