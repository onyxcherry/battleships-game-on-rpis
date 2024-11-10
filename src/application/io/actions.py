import enum
from pydantic.dataclasses import dataclass
from typing import Optional
from domain.field import Field

class InActions(enum.StrEnum):
    Select = "Select"
    Hover = "Hover"
    Confirm = "Confirm"

class OutActions(enum.StrEnum):
    UnknownShots = "UnknownShots"

    HoverShots = "HoverShots"
    HoverShips = "HoverShips"

    MissShots = "MissShots"
    MissShips = "MissShips"

    HitShots = "HitShots"
    HitShips = "HitShips"

    DestroyedShots = "DestroyedShots"
    DestroyedShips = "DestroyedShips"

    Ship = "Ship"
    NoShip = "NoShip"

    PlayerTurn = "PlayerTurn"
    OpponentTurn = "OpponentTurn"

    PlaceShips = "PlaceShips"
    FinishedPlacing = "FinishedPlacing"

class DisplayBoard(enum.StrEnum):
    Ships = "Ships"
    Shots = "Shots"
    Extra = "Extra"

@dataclass(frozen=True)
class ActionEvent:
    action : InActions | OutActions
    tile : Optional[tuple[int, int]] = None
    board : Optional[DisplayBoard] = None

    @property
    def field(self) -> Optional[Field]:
        if self.tile is None:
            return None
        return Field.fromTuple(self.tile)