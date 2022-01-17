from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from copy import deepcopy
from enum import Enum, auto
from pathlib import Path
from random import choice


class Cell:
    def __init__(
        self,
        *,
        row: int,
        col: int,
        value: int | None,
        is_fixed: bool,
        candidates: Iterable[int] | None = None,
    ) -> None:
        self.row = row
        self.col = col
        self.value = value
        self.is_fixed = is_fixed

        self.candidates: set[int]
        if candidates is None:
            self.candidates = set()
        else:
            self.candidates = set(candidates)

    @property
    def coords(self) -> tuple[int, int]:
        return (self.row, self.col)

    def __eq__(self, other: Cell) -> bool:
        return self.coords == other.coords

    def __hash__(self) -> int:
        return hash(self.coords)

    def set_value(self, value: int | None) -> None:
        self.value = value
        self.candidates.clear()

    def toggle_candidate(self, candidate: int) -> None:
        self.value = None

        if candidate in self.candidates:
            self.candidates.remove(candidate)
        else:
            self.candidates.add(candidate)

    def is_sharing_subgrid(self, other: Cell) -> bool:
        return self != other and (
            self.row // 3 == other.row // 3 and self.col // 3 == other.col // 3
        )

    def is_neighbour(self, other: Cell) -> bool:
        return self != other and (
            self.row == other.row
            or self.col == other.col
            or self.is_sharing_subgrid(other)
        )


class Grid:
    def __init__(self, cells: list[Cell]) -> None:
        self._cells = cells

    def __eq__(self, other: Grid) -> bool:
        return self._cells == other._cells

    def __iter__(self) -> Iterator[Cell]:
        return iter(self._cells)

    def __getitem__(self, coords: tuple[int, int]) -> Cell:
        row, col = coords
        return self._cells[row * 9 + col]

    def __setitem__(self, coords: tuple[int, int], cell: Cell) -> None:
        row, col = coords
        self._cells[row * 9 + col] = cell

    @property
    def invalid_cells(self) -> set[Cell]:
        invalid_cells = set()

        for cell in self:
            if cell.value is None or cell in invalid_cells:
                continue

            for other in self:
                if cell.is_neighbour(other) and cell.value == other.value:
                    invalid_cells.add(cell)
                    invalid_cells.add(other)

        return invalid_cells

    @classmethod
    def from_str(cls, s: str) -> Grid:
        cells = [
            Cell(
                row=i // 9,
                col=i % 9,
                value=value if (value := int(ch)) else None,
                is_fixed=bool(value),
            )
            for i, ch in enumerate(s)
        ]

        return cls(cells)


class Difficulty(Enum):
    SUPER_EASY = auto()
    EASY = auto()
    MEDIUM = auto()
    HARD = auto()
    SUPER_HARD = auto()


DIFFICULTY_FILE_MAPPING: dict[Difficulty, str] = {
    Difficulty.SUPER_EASY: "super_easy",
    Difficulty.EASY: "easy",
    Difficulty.MEDIUM: "medium",
    Difficulty.HARD: "hard",
    Difficulty.SUPER_HARD: "super_hard",
}

DATA_PATH = Path(__file__).parent.parent / "data"


def get_puzzle_and_solution(difficulty: Difficulty) -> tuple[str, str]:
    """Gets a random puzzle and its corresponding solution for a given difficulty."""
    csv_path = (DATA_PATH / DIFFICULTY_FILE_MAPPING[difficulty]).with_suffix("csv")
    with open(csv_path, newline="") as csv_file:
        reader = csv.reader(csv_file)

    puzzle, solution = choice(tuple(reader))
    return puzzle, solution


class Game:
    def __init__(self) -> None:
        self.history: list[Cell] = []

    def start(self, difficulty: Difficulty) -> None:
        puzzle, solution = get_puzzle_and_solution(difficulty)

        self.grid = Grid.from_str(puzzle)
        self.solution = Grid.from_str(solution)

        self.history.clear()
        self.selected_cell = self.grid[(0, 0)]

    @property
    def is_completed(self) -> bool:
        return self.grid == self.solution

    def move_up(self) -> None:
        row, col = self.selected_cell.coords
        self.selected_cell = self.grid[((row - 1) % 9, col)]

    def move_down(self) -> None:
        row, col = self.selected_cell.coords
        self.selected_cell = self.grid[((row + 1) % 9, col)]

    def move_left(self) -> None:
        row, col = self.selected_cell.coords
        self.selected_cell = self.grid[(row, (col - 1) % 9)]

    def move_right(self) -> None:
        row, col = self.selected_cell.coords
        self.selected_cell = self.grid[(row, (col + 1) % 9)]

    def undo(self) -> None:
        cell = self.history.pop()

        self.selected_cell = cell
        self.grid[cell.coords] = cell

    def set_value(self, value: int | None) -> None:
        if self.selected_cell.is_fixed:
            return

        self.history.append(deepcopy(self.selected_cell))
        self.selected_cell.set_value(value)

    def toggle_candidate(self, candidate: int) -> None:
        if self.selected_cell.is_fixed:
            return

        self.history.append(deepcopy(self.selected_cell))
        self.selected_cell.toggle_candidate(candidate)
