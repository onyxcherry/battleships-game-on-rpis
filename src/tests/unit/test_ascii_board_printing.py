from domain.boards import print_ascii
from domain.field import Field
from domain.ships import Ship


def tests_rendering_and_printing_board_of_all_ships_states():
    ship1 = Ship.from_parts(wrecked={Field("A3"), Field("A4")}, waving={Field("A5")})
    ship2 = Ship.from_parts(
        wrecked=set(), waving={Field("E5"), Field("F5"), Field("G5")}
    )
    ship3 = Ship.from_parts(wrecked={Field("D9"), Field("D10")}, waving=set())
    ships = [ship1, ship2, ship3]
    expected_output = """
   1 2 3 4 5 6 7 8 9 10
  —————————————————————
A|  ˙ ˙☒˙☒˙☐˙ ˙ ˙ ˙ ˙  |
B|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
C|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
D|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙■˙■ |
E|  ˙ ˙ ˙ ˙☐˙ ˙ ˙ ˙ ˙  |
F|  ˙ ˙ ˙ ˙☐˙ ˙ ˙ ˙ ˙  |
G|  ˙ ˙ ˙ ˙☐˙ ˙ ˙ ˙ ˙  |
H|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
I|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
J|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
  —————————————————————"""
    assert print_ascii(ships) == expected_output
