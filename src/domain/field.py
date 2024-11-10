from typing import Any, Optional
from string import ascii_uppercase


class Field:
    def __init__(self, field_repr: str) -> None:
        if field_repr[0] not in ascii_uppercase:
            raise RuntimeError(f"Bad Y axis: {field_repr[0]}")
        self._y = field_repr[0]
        try:
            x_axis = int(field_repr[1:])
        except ValueError as ex:
            raise RuntimeError(f"Bad X axis: {field_repr[1:]}") from ex
        else:
            self._x = x_axis

    def __eq__(self, obj: Any) -> bool:
        if not isinstance(obj, Field):
            return False
        return self._x == obj._x and self._y == obj._y

    def __hash__(self) -> int:
        return hash(repr(self))
    
    @classmethod
    def fromTuple(cls, pos : tuple[int, int]):
        y = chr(pos[1] + ord('A'))
        x = pos[0] + 1
        return cls(f"{y}{x}")

    @property
    def y(self) -> str:
        return self._y

    @property
    def x(self) -> int:
        return self._x

    @property
    def vector_from_zeros(self) -> tuple[int, int]:
        """(y, x)"""
        y = ord(self.y) - ord("A")
        x = self.x - 1
        return (y, x)

    @property
    def name(self) -> str:
        return f"{self._y}{self._x}"

    def moved_by(self, y: int, x: int) -> Optional["Field"]:
        new_x = self._x + x
        new_y = chr(ord(self._y) + y)
        if 0 <= new_x <= 26 and new_y in ascii_uppercase:
            return Field(f"{new_y}{new_x}")
        return None

    def __str__(self) -> str:
        return f"Field({self.name!s})"

    def __repr__(self) -> str:
        return f"Field({self.name!r})"
