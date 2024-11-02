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
        logger.debug(f"New client connected: {websocket.remote_address}")
        client_data = await websocket.recv()
        client_decoded_data = decode_json_message(client_data)
        client_info = parse_client_info(client_decoded_data)
        client_infos[0] = client_info
        game_info = GameInfo(
            uniqid=uuid4(),
            status=GameStatus.WaitingToStart,
            opponent=None,
            masted_ships=masted_ships_counts,
            board_size=board_size,
        )
        await websocket.send(game_info.stringify())
    elif connected_clients[1] is None:
        connected_clients[1] = websocket
        logger.debug(f"New client connected: {websocket.remote_address}")
        client_data = await websocket.recv()
        client_decoded_data = decode_json_message(client_data)
        client_info = parse_client_info(client_decoded_data)
        client_infos[1] = client_info
        opponent_info = client_infos[0]
        assert opponent_info is not None
        can_game_start = opponent_info.ready and client_info.ready
        game_status = (
            GameStatus.Started if can_game_start else GameStatus.WaitingToStart
        )
        game_info = GameInfo(
            uniqid=uuid4(),
            status=game_status,
            opponent=opponent_info,
            masted_ships=masted_ships_counts,
            board_size=board_size,
        )
        await websocket.send(game_info.stringify())
        game_info_for_client_1 = GameInfo(
            uniqid=uuid4(),
            status=game_status,
            opponent=client_info,
            masted_ships=masted_ships_counts,
            board_size=board_size,
            extra=ExtraInfo(you_start_first=True),
        )
        await websocket.send(game_info_for_client_1.stringify())
    else:
        message = await websocket.recv(decode=True)
        assert isinstance(message, str)
        await broadcast_message(message, websocket)

    # except websockets.ConnectionClosed as e:
    #     logger.debug(f"Client {websocket.remote_address} disconnected: {e}")
    # finally:
    #     connected_clients.remove(websocket)


async def broadcast_message(message: str, sender_socket: ServerConnection):
    for client in connected_clients:
        assert client is not None
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
