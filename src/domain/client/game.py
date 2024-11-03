from typing import Optional
from application.messaging import Message
from domain.attacks import AttackRequest, AttackResult
from domain.field import Field
from domain.boards import ShipsBoard, ShotsBoard
from domain.ships import MastedShips
from dataclasses import dataclass

from domain.client.io.io import IO
from domain.actions import InActions, OutActions
from queue import Queue, Empty
from threading import Thread, Event
from time import sleep


@dataclass(frozen=True)
class ClientStatus:
    ships_placed: bool
    ready: bool


class Game:
    def __init__(self) -> None:
        self._ships_board = ShipsBoard()
        self._attacks_board = ShotsBoard()
        self._ships_placed = False

        self._in_queue = Queue()
        self._out_queue = Queue()
        self._stop_running = Event()
        self._stop_running.clear()
        self._io = IO(self._in_queue, self._out_queue, self._stop_running)

    def place_ships(self, ships: MastedShips) -> None:
        self._ships_board.add_ships(ships)
        self._ships_placed = True

    def attack(self, field: Field) -> None:
        attack_result = self._connection.attack(field)
        self._attacks_board.add_attack(field, attack_result)
    
    def test_in_out(self) -> None:
        self._out_queue.put(OutActions.PlayerTurn)
        while not self._stop_running.is_set():
            try:
                event = self._in_queue.get(timeout=1)
                action = InActions[event.split(';')[0]]
                if action == InActions.HoverShots:
                    print(event)
                    self._out_queue.put(event)
                elif action == InActions.SelectShots:
                    pos = eval(event.split(';')[1])
                    self._out_queue.put(f"{OutActions.MissShots};{pos}")
            except Empty:
                pass

    def inform_about_status(self) -> ClientStatus:
        all_ships_placed = self._ships_board.ships_floating_count == 10
        ready = all_ships_placed and True
        return ClientStatus(ships_placed=all_ships_placed, ready=ready)

    def start(self) -> None:
        io_thread = Thread(target=self._io.run)
        io_thread.start()

        try:
           self.test_in_out()
        except KeyboardInterrupt:
            self._stop_running.set()
        finally:
            io_thread.join()

    def handle_message(self, message: Message) -> Optional[Message]:
        if isinstance(att_req := message.data, AttackRequest):
            status = self._ships_board.process_attack(att_req.field)
            result = AttackResult(field=att_req.field, status=status)
            return result
        elif isinstance(att_res := message.data, AttackResult):
            result = self._attacks_board.add_attack(att_res.field, att_res.status)
            return None
        else:
            raise NotImplementedError()
