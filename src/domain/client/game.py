from typing import Optional
from uuid import uuid4
from application.messaging import GameMessage
from domain.attacks import AttackRequest, AttackResult, AttackResultStatus
from domain.field import Field
from domain.boards import ShipsBoard, ShotsBoard
from domain.ships import MastedShips
from dataclasses import dataclass


@dataclass(frozen=True)
class ClientStatus:
    ships_placed: bool
    ready: bool


class Game:
    def __init__(self) -> None:
        self._ships_board = ShipsBoard()
        self._attacks_board = ShotsBoard()
        self._ships_placed = False

    def place_ships(self, ships: MastedShips) -> None:
        self._ships_board.add_ships(ships)
        self._ships_placed = True

    @property
    def ships_placed(self) -> bool:
        return self._ships_placed

    @property
    def ready(self) -> bool:
        return self._ships_placed and True

    @property
    def all_ships_wrecked(self) -> bool:
        return self._ships_board.ships_floating_count == 0

    def add_attacked_field(self, field: Field) -> None:
        self._attacks_board.add_attack(field, "Unknown")

    def update_attacked_field_status(
        self, field: Field, status: AttackResultStatus
    ) -> None:
        self._attacks_board.add_attack(field, status)

    def inform_about_status(self) -> ClientStatus:
        all_ships_placed = self._ships_board.ships_floating_count == 10
        ready = all_ships_placed and True
        return ClientStatus(ships_placed=all_ships_placed, ready=ready)

    def start(self) -> None:
        pass

    def handle_message(self, message: GameMessage) -> Optional[GameMessage]:
        if isinstance(att_req := message.data, AttackRequest):
            status = self._ships_board.process_attack(att_req.field)
            result = AttackResult(field=att_req.field, status=status)
            message = GameMessage(uniqid=uuid4(), data=result)
            return message
        elif isinstance(att_res := message.data, AttackResult):
            result = self._attacks_board.add_attack(att_res.field, att_res.status)
            return None
        else:
            raise NotImplementedError()
