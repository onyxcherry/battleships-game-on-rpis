#!/usr/bin/env python

import asyncio
import pprint
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
from domain.attacks import AttackRequest
from domain.field import Field
from domain.ships import MastedShips, MastedShipsCounts, Ship
from websockets import ConnectionClosedOK
from websockets.asyncio.client import connect
from domain.client.game import Game
from typing import Optional

server_address = "ws://localhost:4200"

game = Game()

logger = get_logger(__name__)


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


async def place_ships(ships_info: MastedShipsCounts, board_size: int):
    masted_ships = MastedShips(
        single={Ship({Field("A1")}), Ship({Field("H10")}), Ship({Field("J7")})},
        two={Ship({Field("A3"), Field("A4")})},
        three=set(),
        four=set(),
    )
    game.place_ships(masted_ships)
    await asyncio.sleep(0.1)


async def get_next_attack() -> Field:
    field = input("Enter next field to attack:")
    return Field(field)


async def play():
    client_info = ClientInfo(
        uniqid=uuid4(),
        connected=True,
        ships_placed=game.ships_placed,
        ready=game.ready,
        all_ships_wrecked=game.all_ships_wrecked,
    )
    current_game_info: Optional[GameInfo] = None
    placing_ships_task: Optional[asyncio.Task] = None
    next_attack_task: Optional[asyncio.Task] = None

    placed_ships_info_sent: bool = False

    async with connect(server_address) as ws:
        await send(ws, client_info)

        data = await receive(ws)
        game_info = parse_game_info(data)

        if placing_ships_task is None:
            placing_ships_task = asyncio.create_task(
                place_ships(game_info.masted_ships, game_info.board_size)
            )

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

        first_iteration = True
        starting_first = (
            current_game_info.extra is not None
            and current_game_info.extra.you_start_first is True
        )
        next_attack_task = asyncio.create_task(get_next_attack())
        while True:
            if not first_iteration or starting_first:
                if not next_attack_task.done():
                    await asyncio.sleep(0.1)
                    continue
                field_to_attack = await next_attack_task.result()
                attack_request = AttackRequest(field=field_to_attack)
                message = GameMessage(uniqid=uuid4(), data=attack_request)
                await send(ws, message)
                next_attack_task = asyncio.create_task(get_next_attack())
                first_iteration = False

            try:
                async with asyncio.timeout(0.1):
                    data = await receive(ws)
            except TimeoutError:
                pass
            else:
                message = parse_game_message_or_info(data)
                if isinstance(message, GameMessage):
                    result = game.handle_message(message)
                    if result is not None:
                        await send(ws, result)
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
        a = play_task.exception()
        print(f"{a=}")
        logger.exception(ex)
    except KeyboardInterrupt:
        pass
        # play_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
