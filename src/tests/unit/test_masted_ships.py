from domain.boards import ShipsBoard
from domain.field import Field
from domain.ships import (
    MastedShips,
    Ship,
    ships_of_standard_count,
)
from pydantic import ValidationError
import pytest
from config import MastedShipsCounts


def tests_masted_ships_when_counts_matches():
    ships = ships_of_standard_count()
    ships_board = ShipsBoard()
    ships_board.add_ships(ships)


def tests_raising_exception_when_masted_ships_counts_do_not_follow_rules():
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


def tests_creating_masted_ships_from_set():
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
    MastedShips.from_set(ships, counts)
