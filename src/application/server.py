#!/usr/bin/env python

import asyncio
from typing import Optional
from uuid import uuid4
from application.client import decode_json_message
from application.messaging import (
    ClientInfo,
    ExtraInfo,
    GameInfo,
    GameStatus,
    parse_client_info,
)
from config import get_logger
from domain.ships import MastedShipsCounts
from websockets.asyncio.server import serve, ServerConnection
import websockets


connected_clients: list[Optional[ServerConnection]] = [None, None]
client_infos: list[Optional[ClientInfo]] = [None, None]
logger = get_logger(__name__)

masted_ships_counts = MastedShipsCounts(single=4, two=3, three=2, four=1)
board_size = 10


async def listen(websocket: ServerConnection):
    if connected_clients[0] is None:
        connected_clients[0] = websocket
        logger.debug(f"First client connected: {websocket.remote_address}")
        first_client_data = await websocket.recv()
        logger.debug(f"{first_client_data=}")
        client_decoded_data = decode_json_message(first_client_data)
        client_info = parse_client_info(client_decoded_data)
        client_infos[0] = client_info
        game_info = GameInfo(
            uniqid=uuid4(),
            status=GameStatus.WaitingToStart,
            opponent=None,
            masted_ships=masted_ships_counts,
            board_size=board_size,
        )
        game_info_for_first_client = game_info.stringify()
        await websocket.send(game_info_for_first_client)
        logger.debug(f"{game_info_for_first_client=}")
    elif connected_clients[1] is None:
        connected_clients[1] = websocket
        logger.debug(f"Second client connected: {websocket.remote_address}")
        second_client_data = await websocket.recv()
        logger.debug(f"{second_client_data=}")
        client_decoded_data = decode_json_message(second_client_data)
        client_info = parse_client_info(client_decoded_data)
        client_infos[1] = client_info
        opponent_info = client_infos[0]
        assert opponent_info is not None
        can_game_start = opponent_info.ready and client_info.ready
        game_status = (
            GameStatus.Started if can_game_start else GameStatus.WaitingToStart
        )
        game_info_for_second_client = GameInfo(
            uniqid=uuid4(),
            status=game_status,
            opponent=opponent_info,
            masted_ships=masted_ships_counts,
            board_size=board_size,
        )
        game_info_for_second_client_msg = game_info_for_second_client.stringify()
        await websocket.send(game_info_for_second_client_msg)
        logger.debug(f"{game_info_for_second_client_msg=}")
        game_info_for_first_client = GameInfo(
            uniqid=uuid4(),
            status=game_status,
            opponent=client_info,
            masted_ships=masted_ships_counts,
            board_size=board_size,
            extra=ExtraInfo(you_start_first=True),
        )
        game_info_for_first_client_msg = game_info_for_first_client.stringify()
        await connected_clients[0].send(game_info_for_first_client_msg)
        logger.debug(f"{game_info_for_first_client_msg=}")

    while True:
        client_number = 0 if websocket == connected_clients[0] else 1
        message = await websocket.recv(decode=True)
        decoded_message = decode_json_message(message)
        if decoded_message.get("what") == "ClientInfo":
            parsed_client_info = parse_client_info(decoded_message)
            client_infos[client_number] = parsed_client_info
            opponent_conn = connected_clients[int(not client_number)]
            if opponent_conn is None:
                continue
            can_game_start = client_infos[0].ready and client_infos[1].ready
            game_status = (
                GameStatus.Started if can_game_start else GameStatus.WaitingToStart
            )
            extra_start_first = (
                ExtraInfo(you_start_first=True) if client_number == 0 else None
            )
            updated_game_info_for_opponent = GameInfo(
                uniqid=uuid4(),
                status=game_status,
                opponent=parsed_client_info,
                masted_ships=masted_ships_counts,
                board_size=board_size,
                extra=extra_start_first,
            )
            updated_game_info_for_opponent_msg = (
                updated_game_info_for_opponent.stringify()
            )
            await opponent_conn.send(updated_game_info_for_opponent_msg)
            logger.debug(f"{updated_game_info_for_opponent_msg=}")
            if can_game_start:
                opponent_info = client_infos[int(not client_number)]
                updated_game_info_for_client = GameInfo(
                    uniqid=uuid4(),
                    status=game_status,
                    opponent=opponent_info,
                    masted_ships=masted_ships_counts,
                    board_size=board_size,
                    extra=extra_start_first,
                )
                updated_game_info_for_client_msg = (
                    updated_game_info_for_client.stringify()
                )
                await websocket.send(updated_game_info_for_client_msg)
                logger.debug(f"{updated_game_info_for_client_msg=}")
        else:
            await broadcast_message(message, websocket)
            logger.debug(f"{client_number}: {message}")

    # except websockets.ConnectionClosed as e:
    #     logger.debug(f"Client {websocket.remote_address} disconnected: {e}")
    # finally:
    #     connected_clients.remove(websocket)


async def broadcast_message(message: str, sender_socket: ServerConnection):
    for client in connected_clients:
        if client is None:
            continue
        if client != sender_socket:
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                connected_clients.remove(client)


async def main():
    async with serve(listen, "0.0.0.0", 4200):
        await asyncio.get_running_loop().create_future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
