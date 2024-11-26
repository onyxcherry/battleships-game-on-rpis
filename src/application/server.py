#!/usr/bin/env python

import asyncio
import dataclasses
import json
import pprint
from typing import Final, Literal, Optional
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
from config import get_logger, CONFIG
from websockets import ConnectionClosedError, ConnectionClosedOK
from websockets.asyncio.server import serve, ServerConnection


ping_timeout = False
connected_clients: list[Optional[ServerConnection]] = [None, None]
client_infos: list[Optional[ClientInfo]] = [None, None]
logger = get_logger(__name__)


ClientNumber = Literal[0, 1]
ClientName = Literal["FIRST", "SECOND"]
client_names: Final = ["FIRST", "SECOND"]


async def receive(websocket) -> dict:
    data = await websocket.recv()
    decoded = decode_json_message(data)
    formatted = pprint.pformat(decoded, indent=2)
    client_number = get_client_number(websocket)
    assert client_number is not None
    logger.debug(f"Received from {client_names[client_number]}: {formatted}")
    return decoded


async def send(websocket, data: Serializable | dict) -> None:
    if isinstance(data, dict):
        serialized = data
    else:
        serialized = data.serialize()
    json_dumped = json.dumps(serialized)
    await websocket.send(json_dumped)
    formatted = pprint.pformat(serialized, indent=2)
    client_number = get_client_number(websocket)
    assert client_number is not None
    logger.debug(f"Sent to {client_names[client_number]}: {formatted}")


def mark_client_as_disconnected(client_number: ClientNumber) -> None:
    connected_clients[client_number] = None
    client_info = client_infos[client_number]
    assert client_info is not None
    updated_client_info = dataclasses.replace(client_info, connected=False)
    client_infos[client_number] = updated_client_info


async def try_send(websocket: ServerConnection, data: Serializable | dict) -> bool:
    client_number = 0 if websocket == connected_clients[0] else 1
    try:
        await send(websocket, data)
    except ConnectionClosedOK:
        mark_client_as_disconnected(client_number)
        logger.info(
            f"Client {client_names[client_number]} has closed the connection properly"
            + " but they shouldn't have"
        )
        return False
    except ConnectionClosedError:
        mark_client_as_disconnected(client_number)
        logger.info(
            f"Connection to client {client_names[client_number]} has closed improperly"
            + " but it shouldn't have"
        )
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
        masted_ships=CONFIG.masted_ships_counts,
        board_size=CONFIG.board_size,
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
    if client_infos[0] is not None and client_infos[0].all_ships_wrecked:
        game_status = GameStatus.Ended
        first_client_won = False
        second_client_won = True
    elif client_infos[1] is not None and client_infos[1].all_ships_wrecked:
        game_status = GameStatus.Ended
        first_client_won = True
        second_client_won = False

    game_info_for_first_client = GameInfo(
        masted_ships=CONFIG.masted_ships_counts,
        board_size=CONFIG.board_size,
        uniqid=uuid4(),
        status=game_status,
        opponent=client_infos[1],
        extra=ExtraInfo(you_start_first=True, you_won=first_client_won),
    )
    if connected_clients[0] is not None:
        await try_send(connected_clients[0], game_info_for_first_client)

    game_info_for_second_client = GameInfo(
        masted_ships=CONFIG.masted_ships_counts,
        board_size=CONFIG.board_size,
        uniqid=uuid4(),
        status=game_status,
        opponent=client_infos[0],
        extra=ExtraInfo(you_start_first=False, you_won=second_client_won),
    )
    if connected_clients[1] is not None:
        await try_send(connected_clients[1], game_info_for_second_client)


async def welcome_second_client(websocket: ServerConnection) -> None:
    data = await receive(websocket)
    client_info = parse_client_info(data)
    client_infos[1] = client_info
    await update_game_info()


def get_client_number(websocket: Optional[ServerConnection]) -> Optional[ClientNumber]:
    if websocket == connected_clients[0]:
        return 0
    elif websocket == connected_clients[1]:
        return 1
    return None


async def listen(websocket: ServerConnection):
    if connected_clients[0] is None:
        connected_clients[0] = websocket
        logger.debug(f"First client connected: {websocket.remote_address}")
        await welcome_first_client(websocket)
    elif connected_clients[1] is None:
        connected_clients[1] = websocket
        logger.debug(f"Second client connected: {websocket.remote_address}")
        await welcome_second_client(websocket)

    client_number = get_client_number(websocket)
    if client_number is None:
        raise RuntimeError(
            f"Client number is None but websocket={websocket} object is present"
        )

    data = None
    while True:
        try:
            data = await receive(websocket)
        except ConnectionClosedOK:
            logger.info(
                f"Client {client_names[client_number]} has disconnected without error"
            )
            mark_client_as_disconnected(client_number)
            await update_game_info()
        except ConnectionClosedError:
            logger.info(
                f"Connection to client {client_names[client_number]} has terminated"
                + " improperly"
            )
            mark_client_as_disconnected(client_number)
            await update_game_info()

        client_number = get_client_number(websocket)
        if client_number is None:
            return

        # moreover, `data` cannot be stale as disconnected client's handling returned
        assert data is not None
        if data.get("what") == "ClientInfo":
            parsed_client_info = parse_client_info(data)
            client_infos[client_number] = parsed_client_info
            await update_game_info()
        else:
            opponent_conn = connected_clients[int(not client_number)]
            if opponent_conn is not None:
                await try_send(opponent_conn, data)


async def main():
    async with serve(
        listen,
        CONFIG.server_host,
        CONFIG.server_port,
        ping_interval=None,
        ping_timeout=ping_timeout,
    ):
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
