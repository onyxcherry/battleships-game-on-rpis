import asyncio
from threading import Event
import janus
from typing import Tuple, Optional
from threading import Thread
from application.io.actions import InActions, OutActions
from domain.field import Field
from domain.boards import ShipsBoard

# from application.io.pg_io import IO

try:   # distinguish pc and rpi by presence of pygame
    from application.io.pg_io import IO as pg_IO
    print("Pygame IO")
    ON_PC = True

except ImportError:
    from application.io.led_display import Display
    from application.io.rpi_input import Rpi_Input
    print("RPI IO")
    ON_PC = False


class IO:
    def __init__(self, board_size : int):
        self._in_queue : janus.Queue[str] = None
        self._out_queue : janus.Queue[str] = None
        self._stop = Event()
        self._board_size = board_size

        if ON_PC:
            self._io : pg_IO = None
        else:
            self._display : Display = None
            self._input : Rpi_Input = None

    async def get_in_action(self) -> Tuple[InActions, Field]:
        event : str = await self._in_queue.async_q.get(); splitted = event.split(';')
        action = InActions[splitted[0]]
        field_tup : Tuple[int, int] = eval(splitted[1])
        field = Field.fromTuple(field_tup)
        return (action, field)

    async def place_ships(self) -> set[Field]:
        ship_fields : set[Field] = set()

        while not self._stop.is_set():
            try:
                async with asyncio.timeout(0.1):
                    action, field = await self.get_in_action()
            except TimeoutError:
                continue

            y, x = field.vector_from_zeros
            tile = (x,y)
            if action == InActions.HoverShips:
                await self._out_queue.async_q.put(f"{OutActions.HoverShips};{tile}")
            
            elif action == InActions.SelectShips:
                if field in ship_fields:
                    await self._out_queue.async_q.put(f"{OutActions.NoShip};{tile}")
                    ship_fields.remove(field)
                else:
                    await self._out_queue.async_q.put(f"{OutActions.Ship};{tile}")
                    ship_fields.add(field)

            elif action == InActions.FinishedPlacing:
                break
        
        return ship_fields

    async def run(self) -> None:
        self._in_queue = janus.Queue()
        self._out_queue = janus.Queue()
        if ON_PC:
            self._io = pg_IO(self._board_size, self._in_queue.sync_q, self._out_queue.sync_q, self._stop)
            io_t = Thread(target=self._io.run)
            io_t.start()
        else:
            self._display = Display(self._out_queue.sync_q, self._stop)
            self._input = Rpi_Input(self._in_queue.sync_q, self._stop)
            in_t = Thread(target=self._input.run)
            out_t = Thread(target=self._display.run)
            in_t.start()
            out_t.start()

        await self._out_queue.async_q.put(OutActions.PlaceShips)

        test_place_ships_task = asyncio.create_task(self.place_ships())

        try:
            while not self._stop.is_set():
                if test_place_ships_task.done():
                    print(test_place_ships_task.result())
                    break
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            pass
        
        self._stop.set()
        
        if ON_PC:
            io_t.join()
        else:
            in_t.join()
            out_t.join()

        self.clear()
        print(" IO finished")
    
    def clear(self) -> None:
        if not ON_PC:
            self._display.clear()

if __name__ == '__main__':
    io = IO(5)
    asyncio.run(io.run())
