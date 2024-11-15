#!/usr/bin/env python

import asyncio
import pprint
import sys
from uuid import uuid4
from application.messaging import (
    ClientInfo,
    GameInfo,
    GameStatus,
    Serializable,
    decode_json_message,
    parse_game_info,
    GameMessage,
    parse_game_message_or_info,
    AttackRequest,
    AttackResult,
    PossibleAttack
)
from config import get_logger
from domain.field import Field
from domain.ships import MastedShips, Ship
from websockets import ConnectionClosedOK
from websockets.asyncio.client import connect
from domain.client.game import Game
from application.io.io import IO
from typing import Optional

server_address = "ws://localhost:4200"


logger = get_logger(__name__)

ping_timeout = False

game_io = IO()


async def receive(websocket) -> dict:
    data = await websocket.recv()
    decoded = decode_json_message(data)
    formatted = pprint.pformat(decoded, indent=2)
    logger.debug(f"Received: {formatted}")
    return decoded


async def send(websocket, data: Serializable) -> None:
    await websocket.send(data.stringify())
    formatted = pprint.pformat(data.serialize(), indent=2)
    logger.debug(f"Sent: {formatted}")


async def place_ships(game: Game, game_io: IO):
    masted_ships = await game_io.get_masted_ships()
    if masted_ships is not None:
        game.place_ships(masted_ships)
    else:
        logger.warning("No masted ships")


async def read_input() -> Field:
    print("Enter next field to attack:")
    loop = asyncio.get_event_loop()
    fut = loop.create_future()

    def on_input():
        fut.set_result(sys.stdin.readline().strip())

    loop.add_reader(sys.stdin, on_input)

    # Wait for user input
    try:
        result = await fut
    except asyncio.CancelledError:
        loop.remove_reader(sys.stdin)
        return None

    loop.remove_reader(sys.stdin)
    return Field(result)


async def get_possible_or_real_attack(game_io: IO) -> Optional[tuple[Field, bool]]:
    attack_is_real = True
    
    # allow attacking by using either IO class or stdin
    # done, pending = await asyncio.wait([
    #     asyncio.create_task(read_input()),
    #     asyncio.create_task(game_io.get_next_attack())
    # ], return_when=asyncio.FIRST_COMPLETED)

    # field_to_attack = done.pop().result()
    # pending.pop().cancel()
    field_to_attack, attack_is_real = await game_io.get_possible_or_real_attack()
    return field_to_attack, attack_is_real


async def play():
    starting_client_info = ClientInfo(
        uniqid=uuid4(),
        connected=True,
        ships_placed=False,
        ready=False,
        all_ships_wrecked=False,
    )
    current_game_info: Optional[GameInfo] = None
    placing_ships_task: Optional[asyncio.Task] = None
    next_attack_or_possible_attack_task: Optional[asyncio.Task] = None

    placed_ships_info_sent: bool = False

    async with connect(
        server_address, ping_interval=None, ping_timeout=ping_timeout
    ) as ws:
        await send(ws, starting_client_info)

        data = await receive(ws)
        game_info = parse_game_info(data)
        game = Game(
            masted_ships=game_info.masted_ships, board_size=game_info.board_size
        )

        game_io.start(
            masted_ships=game_info.masted_ships, board_size=game_info.board_size
        )

        if placing_ships_task is None:
            placing_ships_task = asyncio.create_task(place_ships(game, game_io))

        while True:
            try:
                async with asyncio.timeout(0.1):
                    data = await receive(ws)
            except TimeoutError:
                pass
            except ConnectionClosedOK:
                pass
            else:
                game_info = parse_game_info(data)
                current_game_info = game_info

            if placing_ships_task.done() and not placed_ships_info_sent:
                client_info = ClientInfo(
                    uniqid=uuid4(),
                    connected=True,
                    ships_placed=game.ships_placed,
                    ready=game.ready,
                    all_ships_wrecked=game.all_ships_wrecked,
                )
                await send(ws, client_info)
                placed_ships_info_sent = True

            if (
                current_game_info is not None
                and current_game_info.status == GameStatus.Started
            ):
                break

        my_turn_to_attack = (
            current_game_info.extra is not None
            and current_game_info.extra.you_start_first is True
        )
        while True:
            if my_turn_to_attack:
                if next_attack_or_possible_attack_task is None:
                    next_attack_or_possible_attack_task = asyncio.create_task(get_possible_or_real_attack(game_io))
                    continue
                elif not next_attack_or_possible_attack_task.done():
                    try:
                        await asyncio.wait_for(asyncio.shield(next_attack_or_possible_attack_task), timeout=0.1)
                    except TimeoutError:
                        continue

                field_to_attack, attack_is_real = next_attack_or_possible_attack_task.result()
                next_attack_or_possible_attack_task = None
                if not attack_is_real:
                    message = Game.possible_attack_of(field_to_attack)
                    await send(ws, message)
                    continue

                message = game.attack(field_to_attack)
                await send(ws, message)
                print(game.show_state())
                my_turn_to_attack = False

            try:
                async with asyncio.timeout(0.1):
                    data = await receive(ws)
            except TimeoutError:
                pass
            else:
                message = parse_game_message_or_info(data)
                if not isinstance(message, GameMessage):
                    current_game_info = message
                else:
                    try:
                        result = game.handle_message(message)
                    except Exception as ex:
                        logger.exception(ex)
                        raise ex
                    print(game.show_state())

                    if isinstance(result, GameMessage):
                        await send(ws, result)
                        my_turn_to_attack = True

                    await game_io.handle_messages(message, result)

            if current_game_info.status == GameStatus.Ended or game.all_ships_wrecked:
                break

        if game.all_ships_wrecked:
            client_info = ClientInfo(
                uniqid=uuid4(),
                connected=True,
                ships_placed=game.ships_placed,
                ready=game.ready,
                all_ships_wrecked=game.all_ships_wrecked,
            )
            await send(ws, client_info)

        while True:
            try:
                async with asyncio.timeout(0.1):
                    data = await receive(ws)
            except TimeoutError:
                pass
            except ConnectionClosedOK:
                pass
            else:
                game_info = parse_game_info(data)
                current_game_info = game_info

            if current_game_info.status == GameStatus.Ended:
                logger.info("Game was ended")
                if (
                    current_game_info.extra is not None
                    and current_game_info.extra.you_won
                ):
                    logger.info("You've won! Congratulations!")
                await ws.close()
                break
    game_io.stop()


async def main():
    play_task = asyncio.create_task(play())
    try:
        done, _ = await asyncio.wait([play_task], return_when=asyncio.FIRST_EXCEPTION)
    except asyncio.CancelledError:
        logger.info("Playing cancelled, exiting...")
        game_io.stop()
        return

    res = done.pop().result()
    if isinstance(res, Exception):
        logger.exception(res)
    elif isinstance(res, BaseException):
        logger.error("Handled BaseException")
        logger.exception(res)
    elif res is not None:
        logger.info(f"Result: {res}")


if __name__ == "__main__":
    asyncio.run(main())
