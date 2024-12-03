import enum
from application.messaging import GameInfo
from config import get_logger
from pydantic.dataclasses import dataclass
from typing import Literal, Optional
from domain.field import Field


class InActions(enum.StrEnum):
    Select = "Select"
    Hover = "Hover"
    Confirm = "Confirm"


class OutActions(enum.StrEnum):
    UnknownShots = "UnknownShots"

    BlinkShips = "BlinkShips"
    BlinkShots = "BlinkShots"

    HoverShots = "HoverShots"
    HoverShips = "HoverShips"

    MissShots = "MissShots"
    MissShips = "MissShips"

    HitShots = "HitShots"
    HitShips = "HitShips"

    DestroyedShots = "DestroyedShots"
    DestroyedShips = "DestroyedShips"

    AroundDestroyedShots = "AroundDestroyedShots"
    AroundDestroyedShips = "AroundDestroyedShips"

    Ship = "Ship"
    NoShip = "NoShip"

    PlayerTurn = "PlayerTurn"
    OpponentTurn = "OpponentTurn"

    PlaceShips = "PlaceShips"
    FinishedPlacing = "FinishedPlacing"


class InfoActions(enum.StrEnum):
    PlayerConnected = "PlayerConnected"
    OpponentConnected = "OpponentConnected"

    PlayerDisconnected = "PlayerDisconnected"
    OpponentDisconnected = "OpponentDisconnected"

    PlayerReady = "PlayerReady"
    OpponentReady = "OpponentReady"

    PlayerWon = "PlayerWon"
    OpponentWon = "OpponentWon"


class DisplayBoard(enum.StrEnum):
    Ships = "Ships"
    Shots = "Shots"
    ShipsBorder = "ShipsBorder"
    ShotsBorder = "ShotsBorder"
    Extra = "Extra"


@dataclass(frozen=True)
class ActionEvent:
    action: InActions | OutActions | InfoActions
    tile: Optional[tuple[int, int]] = None
    board: Optional[DisplayBoard] = None

    @property
    def field(self) -> Optional[Field]:
        if self.tile is None:
            return None
        return Field.fromTuple(self.tile)


class EventInforming:
    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._opponent_connected: Optional[bool] = None
        self._opponent_connected_shown: bool = False
        self._opponent_ready_shown: bool = False

    def react_to(self, game_info: GameInfo) -> None:
        if game_info.opponent is None:
            self._opponent_connected = False
            return
        if self._opponent_connected is None:
            self._opponent_connected = game_info.opponent.connected
        if self._opponent_connected and not game_info.opponent.connected:
            self._logger.debug(InfoActions.OpponentDisconnected)
        if game_info.opponent.connected and not self._opponent_connected_shown:
            self._logger.debug(InfoActions.OpponentConnected)
            self._opponent_connected_shown = True
        if game_info.opponent.ready and not self._opponent_ready_shown:
            self._logger.debug(InfoActions.OpponentReady)
            self._opponent_ready_shown = True

    def player_connected(self) -> None:
        self._logger.debug(InfoActions.PlayerConnected)

    def player_ready(self) -> None:
        self._logger.debug(InfoActions.PlayerReady)

    def player_disconnected(self) -> None:
        self._logger.debug(InfoActions.PlayerDisconnected)

    def won(self, who: Literal["Player", "Opponent"]) -> None:
        if who == "Player":
            self._logger.debug(InfoActions.PlayerWon)
        elif who == "Opponent":
            self._logger.debug(InfoActions.OpponentWon)
        else:
            raise ValueError(f"Invalid side won: {who}")
