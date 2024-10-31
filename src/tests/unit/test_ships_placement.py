from domain.boards import ShipsBoard
from domain.field import Field
from domain.ships import Ship


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
