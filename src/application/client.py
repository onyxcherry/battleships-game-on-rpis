#!/usr/bin/env python

import asyncio
from uuid import uuid4
from application.messaging import (
    ClientInfo,
    GameInfo,
    GameStatus,
    parse_game_info,
    GameMessage,
    parse_game_message_or_info,
)
from config import get_logger
from domain.attacks import AttackRequest
from domain.field import Field
from domain.ships import MastedShipsCounts
from websockets import ConnectionClosedOK
from websockets.asyncio.client import connect
from domain.client.game import Game
from typing import Any, Optional
import json

server_address = "ws://localhost:4200"

game = Game()

logger = get_logger(__name__)


def decode_json_message(data: Any):
    try:
        decoded_message = json.loads(data)
    except json.JSONDecodeError as ex:
        # TODO: inform the other side
        raise RuntimeError("Bad message format!") from ex
    else:
        return decoded_message


async def place_ships(ships_info: MastedShipsCounts, board_size: int):
    await asyncio.sleep(3)


async def get_next_attack() -> Field:
    await asyncio.sleep(2)
    return Field("A4")


async def main():
    client_info = ClientInfo(
        uniqid=uuid4(),
        connected=True,
        ships_placed=False,
        ready=False,
        all_ships_wrecked=False,
    )
    current_game_info: Optional[GameInfo] = None
    placing_ships_task: Optional[asyncio.Task] = None

    placed_ships_info_sent: bool = False

    async with connect(server_address) as ws:
        client_info_msg = client_info.stringify()
        logger.debug(f"{client_info_msg=}")
        await ws.send(client_info_msg)
        logger.debug("Sent initial client info")

        data = await ws.recv()
        logger.debug(f"Received {data=}")
        decoded_data = decode_json_message(data)
        game_info = parse_game_info(decoded_data)

        if placing_ships_task is None:
            placing_ships_task = asyncio.create_task(
                place_ships(game_info.masted_ships, game_info.board_size)
            )

        while True:
            try:
                async with asyncio.timeout(0.1):
                    data = await ws.recv()
            except TimeoutError:
                pass
            except ConnectionClosedOK:
                pass
            else:
                logger.debug(f"Received {data=}")
                decoded_data = decode_json_message(data)
                game_info = parse_game_info(decoded_data)
                current_game_info = game_info

            if placing_ships_task.done() and not placed_ships_info_sent:
                client_info = ClientInfo(
                    uniqid=uuid4(),
                    connected=True,
                    ships_placed=True,
                    ready=True,
                    all_ships_wrecked=False,
                )
                updated_client_info_to_sent = client_info.stringify()
                await ws.send(updated_client_info_to_sent)
                placed_ships_info_sent = True
                logger.debug(f"{updated_client_info_to_sent=}")

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
        while True:
            if not first_iteration or starting_first:
                field_to_attack = await get_next_attack()
                attack_request = AttackRequest(field=field_to_attack)
                message = GameMessage(uniqid=uuid4(), data=attack_request)
                await ws.send(message.stringify())
                first_iteration = False

            try:
                async with asyncio.timeout(0.1):
                    data = await ws.recv()
            except TimeoutError:
                pass
            else:
                decoded_data = decode_json_message(data)
                message = parse_game_message_or_info(decoded_data)
                if isinstance(message, GameMessage):
                    result = game.handle_message(message)
                    if result is not None:
                        await ws.send(result.stringify())
                else:
                    current_game_info = message

            if current_game_info.status == GameStatus.Ended:
                # TODO
                pass
            elif current_game_info.status == GameStatus.InBadState:
                pass


if __name__ == "__main__":
    asyncio.run(main())
