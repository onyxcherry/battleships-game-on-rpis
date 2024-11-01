#!/usr/bin/env python

import asyncio
from uuid import uuid4
from application.messaging import ClientInfo
from config import get_logger
from websockets.asyncio.server import serve
import websockets


connected_clients = set()
logger = get_logger(__name__)


async def listen(websocket):
    connected_clients.add(websocket)
    logger.debug(f"New client connected: {websocket.remote_address}")
    new_client_info = ClientInfo(uniqid=uuid4(), opponent_connected=True)
    await broadcast_message(new_client_info.stringify(), websocket)
    try:
        async for message in websocket:
            logger.debug(f"Received message from {websocket.remote_address}: {message}")
            await broadcast_message(message, websocket)
    except websockets.ConnectionClosed as e:
        logger.debug(f"Client {websocket.remote_address} disconnected: {e}")
    finally:
        connected_clients.remove(websocket)


async def broadcast_message(message: str, sender_socket):
    for client in connected_clients:
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
