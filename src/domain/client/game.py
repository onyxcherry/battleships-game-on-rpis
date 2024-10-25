from dataclasses import dataclass
import enum
from domain.field import Field, AttackResult
from domain.boards import ShipsBoard, ShotsBoard
from domain.ships import MastedShips
from abc import abstractmethod, ABCMeta


class GameStatus(enum.StrEnum):
    WaitingOnPlayer = "WaitingOnPlayer"
    Started = "Started"
    Ended = "Ended"


@dataclass(frozen=True)
class ConnectionInfo:
    pass


class ClientConnection(ABCMeta):
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def connect(self, conn_info: ConnectionInfo) -> None:
        pass

    @abstractmethod
    def attack(self, field: Field) -> AttackResult:
        pass

    @abstractmethod
    def inform_ready_to_start(self) -> GameStatus:
        pass


class Game:
    def __init__(self) -> None:
        self._ships_board = ShipsBoard
        self._attacks_board = ShotsBoard
        # TODO: implement real websocket connection class
        self._connection = ClientConnection()
        self._ships_placed = False

    def place_ships(self, ships: MastedShips) -> None:
        self._ships_board.add_ships(ships)
        self._ships_placed = True

    def attack(self, field: Field) -> None:
        attack_result = self._connection.attack(field)
        self._attacks_board.add_attack(field, attack_result)

    def start(self) -> None:
        pass
