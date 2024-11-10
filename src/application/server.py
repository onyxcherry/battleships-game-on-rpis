#!/usr/bin/env python

import asyncio
import json
import pprint
from typing import Optional
from uuid import uuid4
from application.messaging import (
    ClientInfo,
    ExtraInfo,
    GameInfo,
    GameStatus,
    Serializable,
    decode_json_message,
    parse_client_info,
)
from config import get_logger
from domain.ships import MastedShipsCounts
from websockets import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
from websockets.asyncio.server import serve, ServerConnection


ping_timeout = False
connected_clients: list[Optional[ServerConnection]] = [None, None]
client_infos: list[Optional[ClientInfo]] = [None, None]
logger = get_logger(__name__)

masted_ships_counts = MastedShipsCounts(single=4, two=3, three=2, four=1)
board_size = 10


async def receive(websocket) -> dict:
    data = await websocket.recv()
    decoded = decode_json_message(data)
    formatted = pprint.pformat(decoded, indent=2)
    from_who = "FIRST" if websocket == connected_clients[0] else "SECOND"
    logger.debug(f"Received from {from_who}: {formatted}")
    return decoded


async def send(websocket, data: Serializable | dict) -> None:
    if isinstance(data, dict):
        serialized = data
    else:
        serialized = data.serialize()
    json_dumped = json.dumps(serialized)
    await websocket.send(json_dumped)
    formatted = pprint.pformat(serialized, indent=2)
    to_whom = "FIRST" if websocket == connected_clients[0] else "SECOND"
    logger.debug(f"Sent to {to_whom}: {formatted}")


async def try_send(websocket, data: Serializable | dict) -> bool:
    try:
        await send(websocket, data)
    except ConnectionClosed:
        return False
    else:
        return True


def can_game_start() -> bool:
    return (
        connected_clients[0] is not None
        and connected_clients[1] is not None
        and client_infos[0] is not None
        and client_infos[1] is not None
        and client_infos[0].ready
        and client_infos[1].ready
    )


async def welcome_first_client(websocket: ServerConnection) -> None:
    data = await receive(websocket)
    client_info = parse_client_info(data)
    client_infos[0] = client_info
    game_info = GameInfo(
        masted_ships=masted_ships_counts,
        board_size=board_size,
        uniqid=uuid4(),
        status=GameStatus.WaitingToStart,
        opponent=None,
        extra=ExtraInfo(you_start_first=True),
    )
    await send(websocket, game_info)


async def update_game_info() -> None:
    game_status = GameStatus.WaitingToStart
    if can_game_start():
        game_status = GameStatus.Started

    first_client_won = None
    second_client_won = None
    if client_infos[0].all_ships_wrecked:
        game_status = GameStatus.Ended
        first_client_won = False
        second_client_won = True
    elif client_infos[1] is not None and client_infos[1].all_ships_wrecked:
        game_status = GameStatus.Ended
        first_client_won = True
        second_client_won = False

    game_info_for_first_client = GameInfo(
        masted_ships=masted_ships_counts,
        board_size=board_size,
        uniqid=uuid4(),
        status=game_status,
        opponent=client_infos[1],
        extra=ExtraInfo(you_start_first=True, you_won=first_client_won),
    )
    await send(connected_clients[0], game_info_for_first_client)

    if connected_clients[1] is None:
        return
    game_info_for_second_client = GameInfo(
        masted_ships=masted_ships_counts,
        board_size=board_size,
        uniqid=uuid4(),
        status=game_status,
        opponent=client_infos[0],
        extra=ExtraInfo(you_start_first=False, you_won=second_client_won),
    )
    await send(connected_clients[1], game_info_for_second_client)


async def welcome_second_client(websocket: ServerConnection) -> None:
    data = await receive(websocket)
    client_info = parse_client_info(data)
    client_infos[1] = client_info
    await update_game_info()


async def listen(websocket: ServerConnection):
    if connected_clients[0] is None:
        connected_clients[0] = websocket
        logger.debug(f"First client connected: {websocket.remote_address}")
        await welcome_first_client(websocket)
    elif connected_clients[1] is None:
        connected_clients[1] = websocket
        logger.debug(f"Second client connected: {websocket.remote_address}")
        await welcome_second_client(websocket)

    while True:
        client_number = 0 if websocket == connected_clients[0] else 1
        try:
            data = await receive(websocket)
        except ConnectionClosedOK:
            connected_clients[client_number] = None
            break
        except ConnectionClosedError:
            connected_clients[client_number] = None
            opponent_number = int(not client_number)
            client_infos[opponent_number].connected = False
            if (opponent_conn := connected_clients[opponent_number]) is not None:
                await try_send(opponent_conn, client_infos[opponent_number])
            break

        if data.get("what") == "ClientInfo":
            parsed_client_info = parse_client_info(data)
            client_infos[client_number] = parsed_client_info
            await update_game_info()
        else:
            opponent_conn = connected_clients[int(not client_number)]
            await send(opponent_conn, data)


async def main():
    async with serve(
        listen, "0.0.0.0", 4200, ping_interval=None, ping_timeout=ping_timeout
    ):
        await asyncio.get_running_loop().create_future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
