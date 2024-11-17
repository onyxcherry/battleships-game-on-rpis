import dataclasses
from typing import Optional
from domain.attacks import AttackResultStatus, UnknownStatus
from domain.field import Field
from domain.ships import Ship, MastedShips, ShipStatus


@dataclasses.dataclass
class ShipsFieldsByType:
    floating: set[Field] = dataclasses.field(default_factory=set)
    shot: set[Field] = dataclasses.field(default_factory=set)
    shot_down: set[Field] = dataclasses.field(default_factory=set)
    missed: set[Field] = dataclasses.field(default_factory=set)
    unknown_status: set[Field] = dataclasses.field(default_factory=set)


class LaunchedShipCollidesError(ValueError):
    def __init__(self, msg: str, colliding_fields: list[Field]) -> None:
        self.colliding_fields = colliding_fields


class ShipsBoard:
    def __init__(self) -> None:
        self._ships: dict[Field, Ship] = {}
        self._ships_and_coastal_zones: set[Field] = set()
        self._opponent_missed: set[Field] = set()
        self._opponent_possible_attack: Optional[Field] = None

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
        colliding_fields = []
        for field in sorted(list(ship.fields)):
            if field in self._ships_and_coastal_zones:
                colliding_fields.append(field)
        if len(colliding_fields) > 0:
            colliding_fields_msg = ", ".join(str(field) for field in colliding_fields)
            exception_msg = (
                f"{ship!s} collides with already launched ships due to "
                + f"{colliding_fields_msg}"
            )
            raise LaunchedShipCollidesError(
                exception_msg, colliding_fields=colliding_fields
            )
        self._ships_and_coastal_zones |= ship.fields_with_coastal_zone
        for field in ship.fields:
            self._ships[field] = ship

    def add_ships(self, ships: MastedShips) -> None:
        for ship in sorted([*ships.single, *ships.two, *ships.three, *ships.four]):
            self.add_ship(ship)

    def process_attack(self, field: Field) -> AttackResultStatus:
        self._opponent_possible_attack = None
        if field not in self._ships:
            self._opponent_missed.add(field)
            return AttackResultStatus.Missed
        ship = self._ships[field]
        result = ship.attack(field)
        return result

    def mark_possible_attack(self, field: Field) -> None:
        self._opponent_possible_attack = field

    def represent_graphically(self, size: int) -> str:
        floating_fields = set()
        shot_fields = set()
        shot_down_fields = set()
        missed = self._opponent_missed
        for ship in list(self._ships.values()):
            if ship.status == ShipStatus.Wrecked:
                shot_down_fields |= ship.fields
            else:
                floating_fields |= ship.waving_masts
                shot_fields |= ship.wrecked_masts
        board = create_board(
            ShipsFieldsByType(
                floating=floating_fields,
                shot=shot_fields,
                shot_down=shot_down_fields,
                missed=missed,
            ),
            size,
            self._opponent_possible_attack,
        )
        drawn_board = draw_board(board)
        return drawn_board

    @staticmethod
    def build_ships_from_fields(ships_fields: set[Field]) -> set[Ship]:
        ships: set[Ship] = set()
        fields = list(ships_fields)

        adjacency_vectors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        while len(fields) > 0:
            one_ship_fields: set[Field] = set()
            starting_field = fields[0]
            one_ship_fields.add(starting_field)
            fields_to_visit = list(
                filter(
                    lambda field: field is not None,
                    [starting_field.moved_by(*vector) for vector in adjacency_vectors],
                )
            )
            for adjacent_field in fields_to_visit:
                if adjacent_field in fields:
                    one_ship_fields.add(adjacent_field)
                    field_neighbours = list(
                        filter(
                            lambda field: field is not None,
                            [
                                adjacent_field.moved_by(*vector)
                                for vector in adjacency_vectors
                            ],
                        )
                    )
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


def get_all_ship_fields(all_fields: set[Field], starting: Field) -> set[Field]:
    adjacency_vectors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    ship_fields: set[Field] = {starting}

    # queue of Fields to get their neighbours
    fields_queue: list[Field] = [starting]
    while len(fields_queue) > 0:
        fields_to_visit = list(
            filter(
                lambda field: field is not None,
                [fields_queue[0].moved_by(*vector) for vector in adjacency_vectors],
            )
        )
        for adjacent_field in fields_to_visit:
            if adjacent_field in all_fields and adjacent_field not in ship_fields:
                ship_fields.add(adjacent_field)
                fields_queue.append(adjacent_field)
        fields_queue.remove(fields_queue[0])
    return ship_fields


class ShotsBoard:
    def __init__(self) -> None:
        self._attacks: dict[Field, AttackResultStatus | UnknownStatus] = {}
        self._ships_shot_down: list[Ship] = []

    def add_attack(
        self, field: Field, result: AttackResultStatus | UnknownStatus
    ) -> None:
        self._attacks[field] = result
        if result == AttackResultStatus.ShotDown:
            shot_down_ship_fields = get_all_ship_fields(
                set(self._attacks.keys()), field
            )
            shot_down_ship = Ship.from_parts(
                wrecked=shot_down_ship_fields, waving=set()
            )
            self._ships_shot_down.append(shot_down_ship)

        self.notify_added()

    def notify_added(self) -> None:
        pass

    def represent_graphically(self, size: int) -> str:
        floating_fields = set()
        shot_fields = set()
        shot_down_fields = set()
        unknown_status_fields = set()
        missed_fields = set()

        for shot_down_ship in self._ships_shot_down:
            for field in shot_down_ship.fields:
                shot_down_fields.add(field)

        for field, status in self._attacks.items():
            match status:
                case AttackResultStatus.ShotDown:
                    # handled above
                    pass
                case AttackResultStatus.Shot | AttackResultStatus.AlreadyShot:
                    shot_fields.add(field)
                case AttackResultStatus.Missed:
                    missed_fields.add(field)
                case "Unknown":
                    unknown_status_fields.add(field)
        board = create_board(
            ShipsFieldsByType(
                floating=floating_fields,
                shot=shot_fields,
                shot_down=shot_down_fields,
                missed=missed_fields,
                unknown_status=unknown_status_fields,
            ),
            size,
        )
        drawn_board = draw_board(board)
        return drawn_board


def create_board(
    ships_fields: ShipsFieldsByType,
    size: int = 10,
    opponent_looking: Optional[Field] = None,
) -> list[list[str]]:
    space = "\N{EM SPACE}"
    full_square = "\N{BLACK SQUARE}"
    x_marked = "\N{BALLOT BOX WITH X}"
    edged = "\N{BALLOT BOX}"
    unknown = "?"
    missed = "\N{MULTIPLICATION SIGN}"
    eye = "\N{EYE}"

    matrix = [[space] * size for _ in range(size)]
    for floating_field in ships_fields.floating:
        y, x = floating_field.vector_from_zeros
        matrix[y][x] = edged
    for shot_field in ships_fields.shot:
        y, x = shot_field.vector_from_zeros
        matrix[y][x] = x_marked
    for shot_down_field in ships_fields.shot_down:
        y, x = shot_down_field.vector_from_zeros
        matrix[y][x] = full_square
    for shot_down_field in ships_fields.missed:
        y, x = shot_down_field.vector_from_zeros
        matrix[y][x] = missed
    for unknown_status_field in ships_fields.unknown_status:
        y, x = unknown_status_field.vector_from_zeros
        matrix[y][x] = unknown
    if opponent_looking is not None:
        y, x = opponent_looking.vector_from_zeros
        matrix[y][x] = eye
    return matrix


def draw_board(matrix: list[list[str]]) -> str:
    size = len(matrix)
    half_space = "\N{EN SPACE}"
    space = "\N{EM SPACE}"
    top_bottom_line = "".join([space * 2, "—" * (2 * size + 1)])
    head_numbers = space * 3 + space.join(str(n) for n in range(1, size + 1))
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
