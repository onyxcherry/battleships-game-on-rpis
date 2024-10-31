import copy
from domain.attacks import AttackResultStatus, AttackStatus
from domain.field import Field
from domain.ships import Ship, MastedShips, ShipStatus


class LaunchedShipCollidesError(ValueError):
    pass


class ShipsBoard:
    def __init__(self) -> None:
        self._ships: dict[Field, Ship] = {}

    @property
    def ships_floating_count(self) -> int:
        return len(
            list(
                filter(
                    lambda val: val is not None,
                    map(
                        lambda ship: ship if ship.waving_masts_count > 0 else None,
                        list(self._ships.values()),
                    ),
                )
            )
        )

    def add_ship(self, ship: Ship) -> None:
        for field in ship.fields:
            self._ships[field] = ship

    def add_ships(self, ships: MastedShips) -> None:
        ships_and_coastal_zones: set[Field] = set()
        for ship in [*ships.single, *ships.two, *ships.three, *ships.four]:
            if any(ship.fields in ships_and_coastal_zones):
                raise LaunchedShipCollidesError(
                    f"{ship!s} collides with already launched ships"
                )
            self.add_ship(self, ship)
            ships_and_coastal_zones.add(ship.fields_with_coastal_zone)

    def process_attack(self, field: Field) -> AttackResultStatus:
        if field not in self._ships:
            return AttackResultStatus.Missed
        ship = self._ships[field]
        result = ship.attack(field)
        return result

    @staticmethod
    def build_ships_from_fields(ships_fields: set[Field]) -> set[Ship]:
        ships: set[Ship] = set()
        fields = list(ships_fields)

        adjacency_vectors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        while len(fields) > 0:
            one_ship_fields: set[Field] = set()
            starting_field = fields[0]
            one_ship_fields.add(starting_field)
            fields_to_visit = [
                starting_field.moved_by(*vector) for vector in adjacency_vectors
            ]
            for adjacent_field in fields_to_visit:
                if adjacent_field in fields:
                    one_ship_fields.add(adjacent_field)
                    field_neighbours = [
                        adjacent_field.moved_by(*vector) for vector in adjacency_vectors
                    ]
                    filtered = [
                        new_field
                        for new_field in field_neighbours
                        if new_field in fields and new_field not in one_ship_fields
                    ]
                    fields_to_visit += filtered
            ship = Ship(one_ship_fields)
            ships.add(ship)
            fields = list(set(fields).difference(one_ship_fields))
        return ships


class ShotsBoard:
    def __init__(self) -> None:
        self._attacks: dict[Field, AttackStatus] = []

    def add_attack(self, field: Field, result: AttackResultStatus) -> None:
        self._attacks[field] = result
        self.notify_added()

    def notify_added(self) -> None:
        pass


def print_ascii(ships: list[Ship], size: int = 10) -> None:
    half_space = "\N{EN SPACE}"
    space = "\N{EM SPACE}"
    full_square = "\N{BLACK SQUARE}"
    x_marked = "\N{BALLOT BOX WITH X}"
    edged = "\N{BALLOT BOX}"

    matrix = [[space] * size for _ in range(size)]
    for ship in ships:
        if ship.status == ShipStatus.Wrecked:
            for wrecked_field in ship.fields:
                y, x = wrecked_field.vector_from_zeros
                matrix[y][x] = full_square
            continue
        for field in ship.wrecked_masts:
            y, x = field.vector_from_zeros
            matrix[y][x] = x_marked
        for field in ship.waving_masts:
            y, x = field.vector_from_zeros
            matrix[y][x] = edged

    top_bottom_line = "".join([space * 2, "—" * (2 * size + 1)])
    head_numbers = space * 3 + space.join(str(n) for n in range(1, 11))
    output = [head_numbers, top_bottom_line]
    starting_y_label = ord("A")
    for idx, row in enumerate(matrix):
        line = (
            chr(starting_y_label + idx)
            + "|"
            + half_space
            + "˙".join(row)
            + half_space
            + "|"
        )
        output.append(line)

    output.append(top_bottom_line)
    return "\n".join(output)
