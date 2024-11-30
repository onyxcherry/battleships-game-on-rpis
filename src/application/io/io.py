import asyncio
from threading import Event
from application.messaging import GameMessage, GameInfo
import janus
from typing import Literal, Optional
from threading import Thread
from application.io.actions import (
    InActions,
    OutActions,
    ActionEvent,
    DisplayBoard,
    InfoActions,
)
from domain.field import Field
from domain.boards import ShipsBoard, LaunchedShipCollidesError
from domain.ships import (
    MastedShips,
    ShipBiggerThanAllowedError,
    ShipCountNotConformingError,
)
from config import MastedShipsCounts
from domain.attacks import (
    AttackRequest,
    AttackResult,
    AttackResultStatus,
    PossibleAttack,
)
from domain.client.game import Game

from config import CONFIG, get_logger

from domain.ships import Ship

logger = get_logger(__name__)

if CONFIG.mode == "pygame":
    from application.io.pg_io import IO as pg_IO

elif CONFIG.mode == "rgbled":
    from application.io.led_display import Display
    from application.io.rpi_input import Rpi_Input


class IO:
    def __init__(self):
        self._in_queue: janus.Queue[ActionEvent] = None
        self._out_queue: janus.Queue[ActionEvent] = None
        self._stop = Event()

        self._opponent_connected = False
        self._opponent_ready = False

        if CONFIG.mode == "pygame":
            self._io: pg_IO = None
            self._io_t: Thread = None
        elif CONFIG.mode == "rgbled":
            self._display: Display = None
            self._out_t: Thread = None
            self._input: Rpi_Input = None
            self._in_t: Thread = None

    async def get_in_action(self) -> ActionEvent:
        return await self._in_queue.async_q.get()

    async def put_out_action(self, event: ActionEvent) -> None:
        await self._out_queue.async_q.put(event)

    async def get_masted_ships(self) -> Optional[MastedShips]:

        await self.put_out_action(ActionEvent(OutActions.PlaceShips))

        ships_fields: set[Field] = set()
        masted_ships: MastedShips = None

        try:
            while not self._stop.is_set():
                try:
                    async with asyncio.timeout(0.1):
                        event = await self.get_in_action()
                except TimeoutError:
                    continue

                if event.action == InActions.Hover:
                    await self.put_out_action(
                        ActionEvent(
                            OutActions.HoverShips, event.tile, DisplayBoard.Ships
                        )
                    )

                elif event.action == InActions.Select:
                    if event.field in ships_fields:
                        await self.put_out_action(
                            ActionEvent(
                                OutActions.NoShip, event.tile, DisplayBoard.Ships
                            )
                        )
                        ships_fields.remove(event.field)
                    else:
                        await self.put_out_action(
                            ActionEvent(OutActions.Ship, event.tile, DisplayBoard.Ships)
                        )
                        ships_fields.add(event.field)

                elif event.action == InActions.Confirm:
                    ships = ShipsBoard.build_ships_from_fields(ships_fields)
                    test_board = ShipsBoard()
                    try:
                        masted_ships = MastedShips.from_set(ships, self._masted_counts)
                    except ShipBiggerThanAllowedError as ex:
                        logger.debug(f"Ship bigger than allowed: {ex.ship}")
                        for field in ex.ship.fields:
                            y, x = field.vector_from_zeros
                            await self.put_out_action(
                                ActionEvent(
                                    OutActions.BlinkShips, (x, y), DisplayBoard.Ships
                                )
                            )
                        continue
                    except ShipCountNotConformingError as ex:
                        logger.debug(f"Wrong ship count: {ex.ships}")
                        if len(ex.ships) == 0:
                            logger.debug("Blinking board border")
                            await self.put_out_action(
                                ActionEvent(
                                    OutActions.BlinkShips,
                                    None,
                                    DisplayBoard.ShipsBorder,
                                )
                            )
                            continue
                        for ship in ex.ships:
                            for field in ship.fields:
                                y, x = field.vector_from_zeros
                                await self.put_out_action(
                                    ActionEvent(
                                        OutActions.BlinkShips,
                                        (x, y),
                                        DisplayBoard.Ships,
                                    )
                                )
                        continue

                    try:
                        test_board.add_ships(masted_ships)
                    except LaunchedShipCollidesError as ex:
                        logger.debug(f"Colliding fields: {ex.colliding_fields}")
                        for field in ex.colliding_fields:
                            y, x = field.vector_from_zeros
                            await self.put_out_action(
                                ActionEvent(
                                    OutActions.BlinkShips, (x, y), DisplayBoard.Ships
                                )
                            )
                        masted_ships = None
                        continue

                    break

        except asyncio.CancelledError:
            pass

        await self.put_out_action(ActionEvent(OutActions.FinishedPlacing))
        return masted_ships

    async def get_possible_or_real_attack(self) -> Optional[tuple[Field, bool]]:
        await self.put_out_action(ActionEvent(OutActions.PlayerTurn))

        ret: Optional[tuple[Field, bool]] = None
        event: Optional[ActionEvent] = None

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

    async def player_attack_result(self, result: AttackResult, game: Game) -> None:
        action: OutActions = {
            AttackResultStatus.Missed: OutActions.MissShots,
            AttackResultStatus.Shot: OutActions.HitShots,
            AttackResultStatus.AlreadyShot: OutActions.HitShots,
            AttackResultStatus.ShotDown: OutActions.DestroyedShots,
        }[AttackResultStatus[result.status]]

        y, x = result.field.vector_from_zeros
        tile = (x, y)

        await self.put_out_action(ActionEvent(action, tile, DisplayBoard.Shots))
        # TODO get whole destroyed ship

    async def opponent_attack_result(self, result: AttackResult, game: Game) -> None:
        action: OutActions = {
            AttackResultStatus.Missed: OutActions.MissShips,
            AttackResultStatus.Shot: OutActions.HitShips,
            AttackResultStatus.AlreadyShot: OutActions.HitShips,
            AttackResultStatus.ShotDown: OutActions.DestroyedShips,
        }[AttackResultStatus[result.status]]

        if action == OutActions.DestroyedShips:
            destroyed_ship: Optional[Ship] = None
            for ship in game.ships:
                if not result.field in ship.fields:
                    continue
                destroyed_ship = ship
                break
            for field in destroyed_ship.fields:
                y, x = field.vector_from_zeros
                tile = (x, y)
                await self.put_out_action(
                    ActionEvent(OutActions.DestroyedShips, tile, DisplayBoard.Ships)
                )
            for field in destroyed_ship.coastal_zone:
                y, x = field.vector_from_zeros
                tile = (x, y)
                await self.put_out_action(
                    ActionEvent(
                        OutActions.AroundDestroyedShips, tile, DisplayBoard.Ships
                    )
                )
        else:
            y, x = result.field.vector_from_zeros
            tile = (x, y)

            await self.put_out_action(ActionEvent(action, tile, DisplayBoard.Ships))

    async def opponent_possible_attack(self, possible_atack: PossibleAttack) -> None:
        y, x = possible_atack.field.vector_from_zeros
        tile = (x, y)

        await self.put_out_action(
            ActionEvent(OutActions.HoverShips, tile, DisplayBoard.Ships)
        )

    async def handle_messages(
        self, message: GameMessage, game: Game, result: Optional[GameMessage]
    ) -> None:
        match message.data.type_:
            case AttackResult.type_:
                await self.player_attack_result(message.data, game)
            case AttackRequest.type_:
                await self.opponent_attack_result(result.data, game)
            case PossibleAttack.type_:
                await self.opponent_possible_attack(message.data)
            case _:
                raise ValueError()

    def begin(self) -> None:
        self._in_queue = janus.Queue()
        self._out_queue = janus.Queue()

        if CONFIG.mode == "pygame":
            self._io = pg_IO(self._in_queue.sync_q, self._out_queue.sync_q, self._stop)
            self._io_t = Thread(target=self._io.run)
            self._io_t.start()
        elif CONFIG.mode == "rgbled":
            self._display = Display(self._out_queue.sync_q, self._stop)
            self._input = Rpi_Input(self._in_queue.sync_q, self._stop)
            self._in_t = Thread(target=self._input.run)
            self._out_t = Thread(target=self._display.run)
            self._in_t.start()
            self._out_t.start()
        else:
            raise NotImplementedError(
                f"IO class started in not supported mode: {CONFIG.mode}"
            )

    async def player_connected(
        self, masted_ships: MastedShipsCounts, board_size: int
    ) -> None:
        self._board_size = board_size
        self._masted_counts = masted_ships

        if CONFIG.mode == "pygame":
            self._io.set_board_size(board_size)
        elif CONFIG.mode == "rgbled":
            self._display.set_board_size(board_size)
            self._input.set_board_size(board_size)

        await self.put_out_action(ActionEvent(InfoActions.PlayerConnected))

    async def react_to(self, game_info: GameInfo) -> None:
        if game_info.opponent is None:
            return
        if game_info.opponent.connected and not self._opponent_connected:
            self._opponent_connected = True
            await self.put_out_action(ActionEvent(InfoActions.OpponentConnected))
        if self._opponent_connected and not game_info.opponent.connected:
            self._opponent_connected = False
            await self.put_out_action(ActionEvent(InfoActions.OpponentDisconnected))
        if game_info.opponent.ready and not self._opponent_ready:
            await self.put_out_action(ActionEvent(InfoActions.OpponentReady))

    async def won(self, who: Literal["Player", "Opponent"]) -> None:
        if who == "Player":
            await self.put_out_action(ActionEvent(InfoActions.PlayerWon))
        elif who == "Opponent":
            await self.put_out_action(ActionEvent(InfoActions.OpponentWon))

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

        self.player_connected()

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


if __name__ == "__main__":
    masted_counts = MastedShipsCounts(3, 2, 1, 0)
    io = IO(masted_counts, 5)
    try:
        asyncio.run(io.test_run())
    except KeyboardInterrupt:
        io.stop()
