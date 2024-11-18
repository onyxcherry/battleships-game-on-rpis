from uuid import uuid4
from application.messaging import GameMessage
from config import MastedShipsCounts
from domain.attacks import AttackRequest, AttackResult, AttackResultStatus
from domain.boards import ShipsBoard
from domain.client.game import Game
from domain.field import Field
from domain.ships import MastedShips, Ship


def tests_attacking_ships_via_ships_board():
    ships = [
        Ship({Field("A3"), Field("A4")}),
        Ship({Field("C7"), Field("D7"), Field("C8")}),
        Ship({Field("G8")}),
    ]
    board = ShipsBoard()
    for ship in ships:
        board.add_ship(ship)
    assert board.process_attack(Field("I7")) == AttackResultStatus.Missed
    assert board.ships_floating_count == 3
    assert board.process_attack(Field("G8")) == AttackResultStatus.ShotDown
    assert board.ships_floating_count == 2
    assert board.process_attack(Field("D7")) == AttackResultStatus.Shot
    assert board.ships_floating_count == 2
    assert board.process_attack(Field("D7")) == AttackResultStatus.AlreadyShot
    assert board.ships_floating_count == 2
    assert board.process_attack(Field("D6")) == AttackResultStatus.Missed
    assert board.process_attack(Field("A4")) == AttackResultStatus.Shot
    assert board.process_attack(Field("A3")) == AttackResultStatus.ShotDown
    assert board.ships_floating_count == 1


def tests_attacking_ships_via_game():
    masted_counts = MastedShipsCounts(single=2, two=1, three=1, four=0)
    masted_ships = MastedShips(
        counts=masted_counts,
        single={Ship({Field("G8")}), Ship({Field("J6")})},
        two={Ship({Field("A3"), Field("A4")})},
        three={Ship({Field("C7"), Field("D7"), Field("C8")})},
        four=set(),
    )
    game = Game(masted_counts, 10)
    game.place_ships(masted_ships)
    assert game.masted_ships_counts == masted_counts
    assert game.board_size == 10
    assert game.ships_placed is True
    assert game.all_ships_wrecked is False

    attack_data = game.attack(Field("A3"))
    assert isinstance(attack_data, GameMessage)
    assert attack_data.data == AttackRequest(field=Field("A3"))

    attack_result_data = game.handle_message(attack_data)
    assert isinstance(attack_result_data, GameMessage)
    assert isinstance(attack_result_data.data, AttackResult)
    assert attack_result_data.data.field == Field("A3")
    assert attack_result_data.data.status == AttackResultStatus.Shot

    attack_result_msg = GameMessage(
        uuid4(), AttackResult(Field("J9"), AttackResultStatus.Missed)
    )
    game.handle_message(attack_result_msg)
    possible_attack_msg = game.possible_attack_of(Field("J7"))
    game.handle_message(possible_attack_msg)

    expected_state = """          SHIPS
   1 2 3 4 5 6 7 8 9 10
  —————————————————————
A|  ˙ ˙☒˙☐˙ ˙ ˙ ˙ ˙ ˙  |
B|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
C|  ˙ ˙ ˙ ˙ ˙ ˙☐˙☐˙ ˙  |
D|  ˙ ˙ ˙ ˙ ˙ ˙☐˙ ˙ ˙  |
E|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
F|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
G|  ˙ ˙ ˙ ˙ ˙ ˙ ˙☐˙ ˙  |
H|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
I|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
J|  ˙ ˙ ˙ ˙ ˙☐˙👁˙ ˙ ˙  |
  —————————————————————
   1 2 3 4 5 6 7 8 9 10
  —————————————————————
A|  ˙ ˙?˙ ˙ ˙ ˙ ˙ ˙ ˙  |
B|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
C|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
D|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
E|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
F|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
G|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
H|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
I|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙  |
J|  ˙ ˙ ˙ ˙ ˙ ˙ ˙ ˙×˙  |
  —————————————————————
         ATTACKS"""
    assert game.show_state() == expected_state
