from uuid import UUID
from application.messaging import (
    ClientInfo,
    ExtraInfo,
    GameInfo,
    GameMessage,
    GameStatus,
)
from domain.attacks import AttackRequest, AttackResult, AttackResultStatus
from domain.field import Field
from config import MastedShipsCounts


def tests_serializing_game_message():
    attack_req = AttackRequest(field=Field("A4"))
    message1 = GameMessage(
        uniqid=UUID("2560dff4-d73f-4d09-b1c4-b925ceb368bc"), data=attack_req
    )
    assert message1.serialize() == {
        "uniqid": "2560dff4-d73f-4d09-b1c4-b925ceb368bc",
        "data": {"field": "A4", "type_": "AttackRequest"},
        "what": "GameMessage",
    }
    attack_result = AttackResult(field=Field("A4"), status=AttackResultStatus.Shot)
    message2 = GameMessage(
        uniqid=UUID("e959d394-3664-487d-b021-3d07bea1bd32"), data=attack_result
    )
    assert message2.serialize() == {
        "uniqid": "e959d394-3664-487d-b021-3d07bea1bd32",
        "data": {"field": "A4", "status": "Shot", "type_": "AttackResult"},
        "what": "GameMessage",
    }


def tests_serializing_client_info():
    client_info = ClientInfo(
        uniqid=UUID("9fb087c2-29a0-4f1d-aa76-db1fb90ce1f2"),
        connected=True,
        ships_placed=True,
        ready=False,
        all_ships_wrecked=False,
    )
    assert client_info.serialize() == {
        "uniqid": "9fb087c2-29a0-4f1d-aa76-db1fb90ce1f2",
        "connected": True,
        "ships_placed": True,
        "ready": False,
        "all_ships_wrecked": False,
        "what": "ClientInfo",
    }


def test_serializing_game_info():
    client_info = ClientInfo(
        uniqid=UUID("c1224278-b2c4-4289-ad1e-f74e344ee19d"),
        connected=True,
        ships_placed=True,
        ready=True,
        all_ships_wrecked=False,
    )
    masted_ships_counts = MastedShipsCounts(single=4, two=3, three=2, four=1)
    game_info = GameInfo(
        uniqid=UUID("1e70ec62-aced-4771-97f9-0b945567cf7f"),
        status=GameStatus.Ended,
        opponent=client_info,
        masted_ships=masted_ships_counts,
        board_size=10,
        extra=ExtraInfo(you_start_first=True, you_won=False, error="Some error"),
    )
    assert game_info.serialize() == {
        "uniqid": "1e70ec62-aced-4771-97f9-0b945567cf7f",
        "status": "Ended",
        "opponent": {
            "uniqid": "c1224278-b2c4-4289-ad1e-f74e344ee19d",
            "connected": True,
            "ships_placed": True,
            "ready": True,
            "all_ships_wrecked": False,
            "what": "ClientInfo",
        },
        "masted_ships": {"single": 4, "two": 3, "three": 2, "four": 1},
        "board_size": 10,
        "extra": {"you_start_first": True, "you_won": False, "error": "Some error"},
        "what": "GameInfo",
    }
