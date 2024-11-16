from uuid import UUID
from domain.attacks import AttackRequest
from application.messaging import (
    ClientInfo,
    ExtraInfo,
    GameInfo,
    GameMessage,
    GameStatus,
    parse_game_message_or_info,
)
from domain.field import Field
from config import MastedShipsCounts


def test_parsing_game_message_or_info():
    game_message_data = {
        "uniqid": "2560dff4-d73f-4d09-b1c4-b925ceb368bc",
        "data": {"field": "A4", "type_": "AttackRequest"},
        "what": "GameMessage",
    }
    result1 = parse_game_message_or_info(game_message_data)
    assert result1 == GameMessage(
        uniqid=UUID("2560dff4-d73f-4d09-b1c4-b925ceb368bc"),
        data=AttackRequest(field=Field("A4")),
    )

    game_info_data = {
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

    result2 = parse_game_message_or_info(game_info_data)
    assert result2 == GameInfo(
        uniqid=UUID("1e70ec62-aced-4771-97f9-0b945567cf7f"),
        status=GameStatus.Ended,
        opponent=ClientInfo(
            uniqid=UUID("c1224278-b2c4-4289-ad1e-f74e344ee19d"),
            connected=True,
            ships_placed=True,
            ready=True,
            all_ships_wrecked=False,
        ),
        masted_ships=MastedShipsCounts(single=4, two=3, three=2, four=1),
        board_size=10,
        extra=ExtraInfo(you_start_first=True, you_won=False, error="Some error"),
    )
