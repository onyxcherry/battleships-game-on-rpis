from domain.field import Field, AttackedField, AttackResult
from domain.ships import Ship, MastedShips


class ShipsBoard:
    def __init__(self) -> None:
        self._ships: dict[Field, Ship] = {}

    def add_ship(self, ship: Ship) -> None:
        for field in ship.fields:
            self._ships[field] = ship

    def add_ships(self, ships: MastedShips) -> None:
        for ship in [*ships.single, *ships.two, *ships.three, *ships.four]:
            self.add_ship(self, ship)


class ShotsBoard:
    def __init__(self) -> None:
        self._attacks: list[AttackedField] = []

    def add_attack(self, field: Field, result: AttackResult) -> None:
        attacked_field = AttackedField(field, result)
        self._attacks.append(attacked_field)
        self.notify_added()

    def notify_added(self) -> None:
        pass
