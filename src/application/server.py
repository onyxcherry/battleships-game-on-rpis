#!/usr/bin/env python

import asyncio
import dataclasses
import json
import pprint
import socket
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

logger = get_logger(__name__)

ClientNumber = Literal[0, 1]
ClientName = Literal["FIRST", "SECOND"]
client_names: Final = ["FIRST", "SECOND"]

ping_timeout = False

connected_clients: list[Optional[ServerConnection]] = [None, None]
client_infos: list[Optional[ClientInfo]] = [None, None]
second_client_has_already_connected: bool = False


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


def get_client_number(websocket: Optional[ServerConnection]) -> Optional[ClientNumber]:
    if websocket == connected_clients[0]:
        return 0
    elif websocket == connected_clients[1]:
        return 1
    return None


def mark_client_as_disconnected(client_number: ClientNumber) -> None:
    connected_clients[client_number] = None
    client_info = client_infos[client_number]
    if client_info is None:
        return
    updated_client_info = dataclasses.replace(client_info, connected=False)
    client_infos[client_number] = updated_client_info


async def try_send(websocket: ServerConnection, data: Serializable | dict) -> bool:
    client_number = 0 if websocket == connected_clients[0] else 1
    try:
        await send(websocket, data)
    except ConnectionClosedOK:
        logger.info(
            f"Client {client_names[client_number]} has closed the connection properly"
            + " but they shouldn't have"
        )
        mark_client_as_disconnected(client_number)
        return False
    except ConnectionClosedError:
        logger.info(
            f"Connection to client {client_names[client_number]} has closed improperly"
            + " but it shouldn't have"
        )
        mark_client_as_disconnected(client_number)
        return False
    else:
        return True


async def try_receive(websocket: ServerConnection) -> Optional[dict]:
    client_number = get_client_number(websocket)
    try:
        data = await receive(websocket)
    except ConnectionClosedOK:
        logger.info(
            f"Client {client_names[client_number]} has disconnected without error"
        )
        mark_client_as_disconnected(client_number)
        return None
    except ConnectionClosedError:
        logger.info(
            f"Connection to client {client_names[client_number]} has terminated"
            + " improperly"
        )
        mark_client_as_disconnected(client_number)
        return None
    else:
        return data


def both_clients_connected() -> bool:
    return connected_clients[0] is not None and connected_clients[1] is not None


def can_game_start() -> bool:
    return (
        both_clients_connected()
        and client_infos[0] is not None
        and client_infos[1] is not None
        and client_infos[0].ready
        and client_infos[1].ready
    )


async def welcome_first_client(websocket: ServerConnection) -> bool:
    data = await try_receive(websocket)
    if data is None:
        return False
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
    sent = await try_send(websocket, game_info)
    if not sent:
        return False
    return True


async def welcome_second_client(websocket: ServerConnection) -> bool:
    data = await try_receive(websocket)
    if data is None:
        return False
    client_info = parse_client_info(data)
    client_infos[1] = client_info
    return await update_game_info()


async def update_game_info() -> bool:
    client1_conn = connected_clients[0]
    assert client1_conn is not None

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
    sent_to_client0 = await try_send(client1_conn, game_info_for_first_client)
    if not sent_to_client0:
        return False

    if not second_client_has_already_connected:
        return True

    game_info_for_second_client = GameInfo(
        masted_ships=CONFIG.masted_ships_counts,
        board_size=CONFIG.board_size,
        uniqid=uuid4(),
        status=game_status,
        opponent=client_infos[0],
        extra=ExtraInfo(you_start_first=False, you_won=second_client_won),
    )
    sent_to_client1 = await try_send(connected_clients[1], game_info_for_second_client)
    if not sent_to_client1:
        return False

    return True


async def reset_game() -> None:
    global second_client_has_already_connected
    for idx, client_conn in enumerate(connected_clients):
        client_infos[idx] = None
        if client_conn is None:
            continue
        try:
            await asyncio.wait_for(client_conn.close(1001, "Game resets"), timeout=0.5)
        except TimeoutError:
            pass
        # no except ConnectionClosed is needed (see the source of close())
        connected_clients[idx] = None
    second_client_has_already_connected = False


async def listen(websocket: ServerConnection):
    global second_client_has_already_connected

    if connected_clients[0] is None:
        connected_clients[0] = websocket
        first_client_joined = await welcome_first_client(websocket)
        if not first_client_joined:
            return await reset_game()
        logger.debug(f"First client connected: {websocket.remote_address}")
    elif connected_clients[1] is None:
        connected_clients[1] = websocket
        second_client_has_already_connected = True
        second_client_joined = await welcome_second_client(websocket)
        if not second_client_joined:
            return await reset_game()
        logger.debug(f"Second client connected: {websocket.remote_address}")

    client_number = get_client_number(websocket)
    if client_number is None:
        try:
            await asyncio.wait_for(
                websocket.close(1001, "Both clients are already connected"), timeout=0.2
            )
        except TimeoutError:
            pass
        finally:
            return

    while True:
        data = await try_receive(websocket)
        if data is None:
            return await reset_game()

        if data.get("what") == "ClientInfo":
            parsed_client_info = parse_client_info(data)
            client_infos[client_number] = parsed_client_info
            updated = await update_game_info()
            if not updated:
                return await reset_game()
        else:
            opponent_conn = connected_clients[int(not client_number)]
            sent = await try_send(opponent_conn, data)
            if not sent:
                return await reset_game()


async def main():
    async with serve(
        listen,
        CONFIG.server_host,
        CONFIG.server_port,
        open_timeout=5,
        ping_interval=CONFIG.conn_ping_interval,
        ping_timeout=CONFIG.conn_ping_timeout,
        close_timeout=5,
        family=socket.AF_INET,
    ):
        logger.info(f"Server started at {CONFIG.server_host}:{CONFIG.server_port}")
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
