from domain.attacks import AttackResultStatus
from domain.boards import ShipsBoard, ShotsBoard
from domain.field import Field
from domain.ships import MastedShips, Ship


def tests_rendering_and_printing_ships_board_of_all_ships_states():
    ship1 = Ship.from_parts(wrecked={Field("A3"), Field("A4")}, waving={Field("A5")})
    ship2 = Ship.from_parts(
        wrecked=set(), waving={Field("E5"), Field("F5"), Field("G5")}
    )
    ship3 = Ship.from_parts(wrecked={Field("D9"), Field("D10")}, waving=set())
    ships = MastedShips(single=set(), two={ship3}, three={ship1, ship2}, four=set())
    board = ShipsBoard()
    board.add_ships(ships)
    expected_output = """   1 2 3 4 5 6 7 8 9 10
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
    assert board.represent_graphically(10) == expected_output


def tests_rendering_and_printing_shots_board():
    board = ShotsBoard()
    board.add_attack(Field("A3"), AttackResultStatus.Shot)
    board.add_attack(Field("A3"), AttackResultStatus.AlreadyShot)
    board.add_attack(Field("A2"), AttackResultStatus.Missed)
    board.add_attack(Field("A4"), AttackResultStatus.Missed)
    board.add_attack(Field("G7"), AttackResultStatus.Shot)
    board.add_attack(Field("G8"), AttackResultStatus.Shot)
    board.add_attack(Field("G9"), AttackResultStatus.ShotDown)
    board.add_attack(Field("F2"), "Unknown")

    expected_output = """   1 2 3 4 5 6 7 8 9 10
  —————————————————————
A|  ˙×˙☒˙×˙ ˙ ˙ ˙ ˙ ˙  |
B|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
C|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
D|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
E|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
F|  ˙?˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
G|  ˙ ˙ ˙ ˙ ˙ ˙■˙■˙■˙  |
H|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
I|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
J|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
  —————————————————————"""
    assert board.represent_graphically(10) == expected_output
