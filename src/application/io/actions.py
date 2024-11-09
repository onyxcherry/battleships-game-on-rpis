import enum

class InActions(enum.StrEnum):
    SelectShots = "SelectShots"
    HoverShots = "HoverShots"

    SelectShips = "SelectShips"
    HoverShips = "HoverShips"

    FinishedPlacing = "FinishedPlacing"

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

OUT_SHOTS_ACTIONS : set[OutActions] = {
    OutActions.UnknownShots,
    OutActions.MissShots,
    OutActions.HitShots,
    OutActions.DestroyedShots,
}