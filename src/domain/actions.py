import enum

class Actions(enum.StrEnum):
    SelectShots = "SelectShots"
    HoverShots = "HoverShots"
    HoverShips = "HoverShips"

    MissShots = "MissShots"
    MissShips = "MissShips"

    HitShots = "HitShots"
    HitShips = "HitShips"

    DestroyedShots = "DestroyedShots"
    DestroyedShips = "DestroyedShips"

    Ship = "Ship"

    PlayerTurn = "PlayerTurn"
    OpponentTurn = "OpponentTurn"