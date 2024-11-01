from uuid import UUID
from application.messaging import ClientInfo, GameMessage
from domain.attacks import AttackRequest, AttackResult, AttackResultStatus
from domain.field import Field


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
        uniqid=UUID("9fb087c2-29a0-4f1d-aa76-db1fb90ce1f2"), opponent_connected=True
    )
    assert client_info.serialize() == {
        "uniqid": "9fb087c2-29a0-4f1d-aa76-db1fb90ce1f2",
        "opponent_connected": True,
        "what": "ClientInfo",
    }
