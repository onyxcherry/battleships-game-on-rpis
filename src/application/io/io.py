import asyncio
from threading import Event
from application.messaging import GameMessage
import janus
from typing import Tuple, Optional
from threading import Thread
from application.io.actions import InActions, OutActions, ActionEvent, DisplayBoard
from domain.field import Field
from domain.boards import ShipsBoard, LaunchedShipCollidesError
from domain.ships import MastedShips, ShipBiggerThanAllowedError, ShipCountNotConformingError
from config import MastedShipsCounts
from domain.attacks import AttackRequest, AttackResult, AttackResultStatus, PossibleAttack

from config import CONFIG, get_logger

logger = get_logger(__name__)

if CONFIG.mode == "pygame":
    from application.io.pg_io import IO as pg_IO

elif CONFIG.mode == "rgbled":
    from application.io.led_display import Display
    from application.io.rpi_input import Rpi_Input


class IO:
    def __init__(self):
        self._in_queue : janus.Queue[ActionEvent] = None
        self._out_queue : janus.Queue[ActionEvent] = None
        self._stop = Event()

        if CONFIG.mode == "pygame":
            self._io : pg_IO = None
            self._io_t : Thread = None
        elif CONFIG.mode == "rgbled":
            self._display : Display = None
            self._out_t : Thread = None
            self._input : Rpi_Input = None
            self._in_t : Thread = None

    async def get_in_action(self) -> ActionEvent:
        return await self._in_queue.async_q.get()
    
    async def put_out_action(self, event : ActionEvent) -> None:
        await self._out_queue.async_q.put(event)

    async def get_masted_ships(self) -> Optional[MastedShips]:

        await self.put_out_action(ActionEvent(OutActions.PlaceShips))

        ships_fields : set[Field] = set()
        masted_ships : MastedShips = None

        try:
            while not self._stop.is_set():
                try:
                    async with asyncio.timeout(0.1):
                        event = await self.get_in_action()
                except TimeoutError:
                    continue

                if event.action == InActions.Hover:
                    await self.put_out_action(
                        ActionEvent(OutActions.HoverShips, event.tile, DisplayBoard.Ships)
                        )
                
                elif event.action == InActions.Select:
                    if event.field in ships_fields:
                        await self.put_out_action(
                            ActionEvent(OutActions.NoShip, event.tile, DisplayBoard.Ships)
                        )
                        ships_fields.remove(event.field)
                    else:
                        await self.put_out_action(
                            ActionEvent(OutActions.Ship, event.tile, DisplayBoard.Ships)
                        )
                        ships_fields.add(event.field)

                elif event.action == InActions.Confirm:
                    try:
                        ships = ShipsBoard.build_ships_from_fields(ships_fields)
                        masted_ships = MastedShips.from_set(ships, self._masted_counts)
                        test_board = ShipsBoard()
                        test_board.add_ships(masted_ships)
                        break
                    except LaunchedShipCollidesError as ex:
                        logger.warning(ex.colliding_fields)
                        # TODO blink colliding fields
                    except ShipBiggerThanAllowedError as ex:
                        logger.warning(ex.ship)
                        # TODO blink ship
                    except ShipCountNotConformingError as ex:
                        logger.exception(ex.ships)
                        # TODO blink ships


        except asyncio.CancelledError:
            pass

        await self.put_out_action(ActionEvent(OutActions.FinishedPlacing))
        return masted_ships
    
    async def get_possible_or_real_attack(self) -> Optional[tuple[Field, bool]]:
        await self.put_out_action(ActionEvent(OutActions.PlayerTurn))

        ret : Optional[tuple[Field, bool]] = None
        event : Optional[ActionEvent] = None

        while not self._stop.is_set():
            try:
                async with asyncio.timeout(0.1):
                    event = await self.get_in_action()
            except TimeoutError:
                continue

            if event.action == InActions.Hover:
                await self.put_out_action(
                    ActionEvent(OutActions.HoverShots, event.tile, DisplayBoard.Shots)
                )
                ret = event.field, False
                break
            
            if event.action == InActions.Select:
                await self.put_out_action(
                    ActionEvent(OutActions.UnknownShots, event.tile, DisplayBoard.Shots)
                )
                await self.put_out_action(ActionEvent(OutActions.OpponentTurn))
                ret = event.field, True
                break
        
        return ret
    
    async def player_attack_result(self, result : AttackResult) -> None:
        action : OutActions = {
            AttackResultStatus.Missed : OutActions.MissShots,
            AttackResultStatus.Shot : OutActions.HitShots,
            AttackResultStatus.AlreadyShot : OutActions.HitShots, # TODO inform player
            AttackResultStatus.ShotDown : OutActions.DestroyedShots
        }[AttackResultStatus[result.status]]

        y, x = result.field.vector_from_zeros
        tile = (x,y)

        await self.put_out_action(ActionEvent(action, tile, DisplayBoard.Shots))
    
    async def opponent_attack_result(self, result : AttackResult) -> None:
        action : OutActions = {
            AttackResultStatus.Missed : OutActions.MissShips,
            AttackResultStatus.Shot : OutActions.HitShips,
            AttackResultStatus.AlreadyShot : OutActions.HitShips, # TODO inform player
            AttackResultStatus.ShotDown : OutActions.DestroyedShips
        }[AttackResultStatus[result.status]]

        y, x = result.field.vector_from_zeros
        tile = (x,y)

        await self.put_out_action(ActionEvent(action, tile, DisplayBoard.Ships))
    
    async def opponent_possible_attack(self, possible_atack: PossibleAttack) -> None:
        y, x = possible_atack.field.vector_from_zeros
        tile = (x,y)

        await self.put_out_action(ActionEvent(OutActions.HoverShips,tile, DisplayBoard.Ships))

    async def handle_messages(self, message: GameMessage, result: Optional[GameMessage]) -> None:
        match message.data.type_:
            case AttackResult.type_:
                await self.player_attack_result(message.data)
            case AttackRequest.type_:
                await self.opponent_attack_result(result.data)
            case PossibleAttack.type_:
                await self.opponent_possible_attack(message.data)
            case _:
                raise ValueError()

    def start(self, masted_ships: MastedShipsCounts, board_size: int) -> None:
        self._in_queue = janus.Queue()
        self._out_queue = janus.Queue()
        self._board_size = board_size
        self._masted_counts = masted_ships

        if CONFIG.mode == "pygame":
            self._io = pg_IO(self._board_size, self._in_queue.sync_q, self._out_queue.sync_q, self._stop)
            self._io_t = Thread(target=self._io.run)
            self._io_t.start()
        elif CONFIG.mode == "rgbled":
            self._display = Display(self._board_size, self._out_queue.sync_q, self._stop)
            self._input = Rpi_Input(self._board_size, self._in_queue.sync_q, self._stop)
            self._in_t = Thread(target=self._input.run)
            self._out_t = Thread(target=self._display.run)
            self._in_t.start()
            self._out_t.start()
        else:
            raise NotImplementedError(f"IO class started in incorrect mode: {CONFIG.mode}")
    
    def stop(self) -> None:
        self._stop.set()
        
        if CONFIG.mode == "pygame":
            self._io_t.join()
        elif CONFIG.mode == "rgbled":
            self._in_t.join()
            self._out_t.join()

        self.clear()
    
    def has_finished(self) -> bool:
        return self._stop.is_set()

    async def test_run(self) -> None:

        self.start()

        test_place_ships_task = asyncio.create_task(self.get_masted_ships())
        ships_task_p = False
        while not self._stop.is_set():
            if test_place_ships_task.done() and not ships_task_p:
                print(test_place_ships_task.result())
                ships_task_p = True
                break
            await asyncio.sleep(0.1)
        
        print(await self.get_possible_or_real_attack())
        await asyncio.sleep(4)
        
        self.stop()
    
    def clear(self) -> None:
        if CONFIG.mode == "rgbled":
            self._display.clear()

if __name__ == '__main__':
    masted_counts = MastedShipsCounts(3,2,1,0)
    io = IO(masted_counts,5)
    try:
        asyncio.run(io.test_run())
    except KeyboardInterrupt:
        io.stop()
