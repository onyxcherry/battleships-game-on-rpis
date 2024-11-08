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
    # game.masted_ships_counts
    # masted_ships = MastedShips(
    #     single={Ship({Field("A1")}), Ship({Field("H10")}), Ship({Field("J7")})},
    #     two={Ship({Field("A3"), Field("A4")})},
    #     three=set(),
    #     four=set(),
    # )
    # game.place_ships(masted_ships)
    # await asyncio.sleep(0.1)
    
    masted_shpis = await game_io.get_masted_ships()
    game.place_ships(masted_shpis)


async def read_input() -> str:
    loop = asyncio.get_event_loop()
    fut = loop.create_future()

    def on_input():
        fut.set_result(sys.stdin.readline().strip())

    loop.add_reader(sys.stdin, on_input)

    # Wait for user input
    result = await fut

    loop.remove_reader(sys.stdin)
    return result


async def get_next_attack() -> Field:
    print("Enter next field to attack:")
    input_task = asyncio.create_task(read_input())
    await input_task
    field = input_task.result()
    return Field(field)


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
    next_attack_task: Optional[asyncio.Task] = None

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

        game_io = IO(
            masted_ships=game_info.masted_ships, board_size=game_info.board_size
        )
        game_io.start()

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
                if next_attack_task is None:
                    next_attack_task = asyncio.create_task(get_next_attack())
                    continue
                elif not next_attack_task.done():
                    await asyncio.sleep(0.1)
                    continue

                field_to_attack = next_attack_task.result()
                message = game.attack(field_to_attack)
                await send(ws, message)
                print(game.show_state())
                next_attack_task = asyncio.create_task(get_next_attack())
                my_turn_to_attack = False

            try:
                async with asyncio.timeout(0.1):
                    data = await receive(ws)
            except TimeoutError:
                pass
            else:
                message = parse_game_message_or_info(data)
                if isinstance(message, GameMessage):
                    try:
                        result = game.handle_message(message)
                    except Exception as ex:
                        logger.exception(ex)
                        raise ex
                    print(game.show_state())

                    if isinstance(result, GameMessage):
                        await send(ws, result)
                        my_turn_to_attack = True
                else:
                    current_game_info = message

            if current_game_info.status == GameStatus.Ended:
                # TODO
                pass
            elif current_game_info.status == GameStatus.InBadState:
                pass


async def main():
    play_task = asyncio.create_task(play())
    try:
        await asyncio.gather(play_task, return_exceptions=True)
    except Exception as ex:
        exc = play_task.exception()
        logger.exception(exc)
        logger.exception(ex)
    # except KeyboardInterrupt:
    #     pass
    # play_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
