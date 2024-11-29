from domain.boards import LaunchedShipCollidesError, ShipsBoard
from domain.field import Field
from domain.ships import MastedShips, Ship, ships_of_standard_count
import pytest
from config import MastedShipsCounts


def tests_sorting_fields():
    ships = [
        Field("A3"),
        Field("A1"),
        Field("B3"),
        Field("B2"),
        Field("G1"),
        Field("G7"),
    ]
    assert sorted(ships) == [
        Field("A1"),
        Field("A3"),
        Field("B2"),
        Field("B3"),
        Field("G1"),
        Field("G7"),
    ]


def tests_infering_coastal_zone_of_ship():
    ship = Ship.from_parts(
        waving={
            Field("G7"),
            Field("F5"),
            Field("G5"),
            Field("G6"),
            Field("E5"),
        },
        wrecked=set(),
    )
    expected_coastal_zone = {
        Field("D4"),
        Field("D5"),
        Field("D6"),
        Field("E4"),
        Field("E6"),
        Field("F4"),
        Field("F6"),
        Field("F7"),
        Field("F8"),
        Field("G4"),
        Field("G8"),
        Field("H4"),
        Field("H5"),
        Field("H6"),
        Field("H7"),
        Field("H8"),
    }

    assert ship.coastal_zone == expected_coastal_zone


def tests_adding_to_ships_board_masted_ships_of_standard_count():
    ships = ships_of_standard_count()
    ships_board = ShipsBoard()
    ships_board.add_ships(ships)


def tests_adding_to_ships_board_not_colliding_ships():
    ships_board = ShipsBoard()
    ship1 = Ship({Field("A3"), Field("A4")})
    ship2 = Ship({Field("D8"), Field("C8")})
    ships_board.add_ship(ship1)
    ships_board.add_ship(ship2)


def tests_raising_exception_when_adding_colliding_ships_one_by_one():
    ships_board = ShipsBoard()
    ship1 = Ship({Field("A3"), Field("A4")})
    ship2 = Ship({Field("B5"), Field("C5")})
    ships_board.add_ship(ship1)
    with pytest.raises(LaunchedShipCollidesError) as ex:
        _ = ships_board.add_ship(ship2)
    assert ex.value.colliding_fields == [Field("B5")]


def tests_raising_exception_when_adding_colliding_ships_all_at_once():
    ships_board = ShipsBoard()
    ship1 = Ship({Field("A3"), Field("A4")})
    ship2 = Ship({Field("B5"), Field("C5")})
    masted_ships = MastedShips(
        counts=MastedShipsCounts(single=0, two=2, three=0, four=0),
        single=set(),
        two={ship1, ship2},
        three=set(),
        four=set(),
    )
    with pytest.raises(LaunchedShipCollidesError) as ex:
        _ = ships_board.add_ships(masted_ships)
    assert ex.value.colliding_fields == [Field("B5")]
