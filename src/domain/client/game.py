from typing import Optional
from uuid import uuid4
from application.messaging import GameMessage
from domain.attacks import AttackRequest, AttackResult
from domain.field import Field
from domain.boards import ShipsBoard, ShotsBoard
from domain.ships import MastedShips, MastedShipsCounts
from dataclasses import dataclass

from domain.client.display.pg_display import Display
from domain.actions import InActions, OutActions
from queue import Queue
from threading import Thread



@dataclass(frozen=True)
class ClientStatus:
    ships_placed: bool
    ready: bool


class Game:
    def __init__(self, masted_ships: MastedShipsCounts, board_size: int) -> None:
        self._masted_ships = masted_ships
        self._board_size = board_size
        self._ships_board = ShipsBoard()
        self._attacks_board = ShotsBoard()
        self._ships_placed = False

        self._in_queue = Queue()
        self._out_queue = Queue()
        self._display = Display(self._in_queue, self._out_queue)
        self._display_thread = Thread(target=self._display.run)

    def place_ships(self, ships: MastedShips) -> None:
        self._ships_board.add_ships(ships)
        self._ships_placed = True

    @property
    def masted_ships_counts(self) -> MastedShipsCounts:
        return self._masted_ships

    @property
    def board_size(self) -> int:
        return self._board_size

    @property
    def ships_placed(self) -> bool:
        return self._ships_placed

    @property
    def ready(self) -> bool:
        return self._ships_placed and True

    @property
    def all_ships_wrecked(self) -> bool:
        return self._ships_board.ships_floating_count == 0

    def attack(self, field: Field) -> GameMessage:
        self._attacks_board.add_attack(field, "Unknown")
        attack_request = AttackRequest(field=field)
        message = GameMessage(uniqid=uuid4(), data=attack_request)
        return message

    def handle_message(self, message: GameMessage) -> Optional[GameMessage]:
        if isinstance(att_req := message.data, AttackRequest):
            status = self._ships_board.process_attack(att_req.field)
            result = AttackResult(field=att_req.field, status=status)
            message = GameMessage(uniqid=uuid4(), data=result)
            return message
        elif isinstance(att_res := message.data, AttackResult):
            self._attacks_board.add_attack(att_res.field, att_res.status)
            return None
        else:
            raise NotImplementedError()

    def show_state(self) -> str:
        space = "\N{EM SPACE}"
        my_ships = self._ships_board.represent_graphically(self._board_size)
        my_attacks = self._attacks_board.represent_graphically(self._board_size)
        state = [f"{space*10}SHIPS", my_ships, my_attacks, f"{space*9}ATTACKS"]
        return "\n".join(state)
