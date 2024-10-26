from dataclasses import dataclass
import enum
from domain.field import Field, AttackResult
from domain.boards import ShipsBoard, ShotsBoard
from domain.ships import MastedShips
from domain.client.pg_display import Display
from domain.actions import Actions
from queue import Queue
from threading import Thread
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
        # self._connection = ClientConnection()
        self._ships_placed = False

        self._in_queue = Queue()
        self._out_queue = Queue()
        self._display = Display(self._in_queue, self._out_queue)
        self._display_thread = Thread(target=self._display.run)

    def place_ships(self, ships: MastedShips) -> None:
        self._ships_board.add_ships(ships)
        self._ships_placed = True

    def attack(self, field: Field) -> None:
        attack_result = self._connection.attack(field)
        self._attacks_board.add_attack(field, attack_result)
    
    def test_in_out(self) -> None:
        self._out_queue.put(Actions.PlayerTurn)
        while True:
            event = self._in_queue.get()
            action = Actions[event.split(';')[0]]
            if action == Actions.HoverShots:
                print(event)
                self._out_queue.put(event)
            elif action == Actions.SelectShots:
                pos = eval(event.split(';')[1])
                self._out_queue.put(f"{Actions.MissShots};{pos}")


    def start(self) -> None:
        test_in_out_t = Thread(target=self.test_in_out)
        test_in_out_t.daemon = True

        self._display_thread.start()
        test_in_out_t.start()

        self._display_thread.join()
