#!/usr/bin/env python

import asyncio
import pprint
import socket
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
from config import CLIENT_CONFIG, get_logger, CONFIG
from domain.field import Field
from domain.ships import MastedShips, ships_of_standard_count
from websockets import ConnectionClosedError, ConnectionClosedOK
from websockets.asyncio.client import connect
from domain.client.game import Game
from application.io.io import IO
from typing import Optional


logger = get_logger(__name__)

ping_timeout = False

game_io = IO()

connect_attempt_count = 0

placing_ships_task: Optional[asyncio.Task] = None
next_attack_or_possible_attack_task: Optional[asyncio.Task] = None

show_possible_attacks = False


async def receive(websocket) -> dict:
    data = await websocket.recv()
    decoded = decode_json_message(data)
    formatted = pprint.pformat(decoded, indent=2)
    if "PossibleAttack" not in formatted or show_possible_attacks:
        logger.debug(f"Received: {formatted}")
    return decoded


async def send(websocket, data: Serializable) -> None:
    await websocket.send(data.stringify())
    formatted = pprint.pformat(data.serialize(), indent=2)
    if "PossibleAttack" not in formatted or show_possible_attacks:
        logger.debug(f"Sent: {formatted}")


async def place_ships(game: Game) -> None:
    if CONFIG.mode == "terminal":
        all_ships = ships_of_standard_count()
        counts = game.masted_ships_counts
        masted_ships = MastedShips(
            counts=counts,
            single=set(list(all_ships.single)[: counts.single]),
            two=set(list(all_ships.two)[: counts.two]),
            three=set(list(all_ships.three)[: counts.three]),
            four=set(list(all_ships.four)[: counts.four]),
        )
        game.place_ships(masted_ships)
    else:
        masted_ships = await game_io.get_masted_ships()
        if masted_ships is not None:
            game.place_ships(masted_ships)
        else:
            logger.warning("No masted ships")


def show_state(game: Game) -> None:
    if CONFIG.mode == "terminal":
        print(game.show_state())


async def read_input() -> tuple[Field, bool]:
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
        raise RuntimeError("Cancelled, no field returned")

    loop.remove_reader(sys.stdin)
    if not isinstance(result, str):
        raise RuntimeError(
            f"Reading field from stdin failed weirdly; type: {type(result)}"
        )
    is_real = True
    if result.startswith(">"):
        is_real = False

    return (Field(result.lstrip(">")), is_real)


async def get_possible_or_real_attack() -> Optional[tuple[Field, bool]]:
    if CONFIG.mode == "terminal":
        return await read_input()
    else:
        return await game_io.get_possible_or_real_attack()


def cancel_running_user_tasks() -> None:
    if (
        placing_ships_task is not None
        and not placing_ships_task.done()
        and not placing_ships_task.cancelled()
    ):
        placing_ships_task.cancel()

    if (
        next_attack_or_possible_attack_task is not None
        and not next_attack_or_possible_attack_task.done()
        and not next_attack_or_possible_attack_task.cancelled()
    ):
        next_attack_or_possible_attack_task.cancel()


def stop_all():
    game_io.stop()


async def play():
    global placing_ships_task
    global next_attack_or_possible_attack_task
    global connect_attempt_count

    starting_client_info = ClientInfo(
        uniqid=uuid4(),
        connected=True,
        ships_placed=False,
        ready=False,
        all_ships_wrecked=False,
    )
    current_game_info: Optional[GameInfo] = None

    placed_ships_info_sent: bool = False

    server_address = f"ws://{CONFIG.server_host}:{CONFIG.server_port}"
    logger.info(f"Will try to connect to {server_address}")

    async with connect(
        server_address,
        ping_interval=None,
        ping_timeout=ping_timeout,
        family=socket.AF_INET,
    ) as ws:
        await send(ws, starting_client_info)
        connect_attempt_count = 0

        data = await receive(ws)
        current_game_info = parse_game_info(data)

        game = Game(
            masted_ships=current_game_info.masted_ships,
            board_size=current_game_info.board_size,
        )

        await game_io.player_connected(
            masted_ships=current_game_info.masted_ships,
            board_size=current_game_info.board_size,
        )
        await game_io.react_to(current_game_info)

        placing_ships_task = asyncio.create_task(place_ships(game))

        while True:
            try:
                async with asyncio.timeout(0.1):
                    data = await receive(ws)
            except TimeoutError:
                pass
            else:
                current_game_info = parse_game_info(data)
                await game_io.react_to(current_game_info)

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

        show_state(game)

        my_turn_to_attack = (
            current_game_info.extra is not None
            and current_game_info.extra.you_start_first is True
        )
        while True:
            if my_turn_to_attack:
                if next_attack_or_possible_attack_task is None:
                    next_attack_or_possible_attack_task = asyncio.create_task(
                        get_possible_or_real_attack()
                    )
                    continue
                elif not next_attack_or_possible_attack_task.done():
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(next_attack_or_possible_attack_task),
                            timeout=0.1,
                        )
                    except TimeoutError:
                        continue

                res = next_attack_or_possible_attack_task.result()
                if res is None:
                    continue
                field_to_attack, attack_is_real = res
                next_attack_or_possible_attack_task = None
                if not attack_is_real:
                    message = Game.possible_attack_of(field_to_attack)
                    await send(ws, message)
                    continue

                message = game.attack(field_to_attack)
                await send(ws, message)
                show_state(game)
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
                    show_state(game)

                    if isinstance(result, GameMessage):
                        await send(ws, result)
                        my_turn_to_attack = True

                    await game_io.handle_messages(message, game, result)

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
            else:
                current_game_info = parse_game_info(data)
                await game_io.react_to(current_game_info)

            if current_game_info.status == GameStatus.Ended:
                logger.info("Game was ended")
                if current_game_info.extra is not None:
                    if current_game_info.extra.you_won:
                        logger.info("You've won! Congratulations!")
                    who_won = (
                        "Player" if current_game_info.extra.you_won else "Opponent"
                    )
                    await game_io.won(who_won)
                await asyncio.sleep(CLIENT_CONFIG.game_ended_state_show_seconds)
                await ws.close()
                break

    await game_io.player_disconnected()


async def main():
    global connect_attempt_count

    if CONFIG.mode != "terminal":
        game_io.begin()

    while True:
        play_task = asyncio.create_task(play())
        try:
            done, _ = await asyncio.wait(
                [play_task], return_when=asyncio.FIRST_EXCEPTION
            )
        except asyncio.CancelledError:
            logger.info("Playing cancelled, exiting...")
            stop_all()
            return
        try:
            res = done.pop().result()
        except ConnectionRefusedError as ex:
            logger.error(ex)
        except ConnectionClosedOK as ex:
            logger.warning(f"Client disconnected (OK): {ex}")
        except ConnectionClosedError as ex:
            logger.error(f"Client disconnected (ERROR): {ex}")
        except Exception as ex:
            logger.error("Handled Exception")
            logger.exception(ex)
        except BaseException as ex:
            logger.error("Handled BaseException")
            logger.exception(ex)
        else:
            if res is not None:
                logger.info(f"Result: {res}")
            else:
                logger.info("Returned None")

        waiting_seconds = (
            0.05 * 2**connect_attempt_count if connect_attempt_count <= 8 else 3.0
        )
        connect_attempt_count += 1
        if waiting_seconds >= CLIENT_CONFIG.min_duration_to_show_animation_in_seconds:
            await game_io.player_disconnected()

        cancel_running_user_tasks()
        try:
            await asyncio.sleep(waiting_seconds)
        except asyncio.CancelledError:
            logger.info("Playing (specifically sleeping) cancelled, exiting...")
            stop_all()
            return


if __name__ == "__main__":
    asyncio.run(main())
