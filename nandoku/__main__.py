from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from enum import Enum, auto
from pathlib import Path
from random import choice
from tkinter import Frame, Tk
from typing import Literal

CellValue = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]


class Cell:
    def __init__(
        self,
        row: int,
        col: int,
        value: CellValue | None,
        is_fixed: bool,
        candidates: Iterable[int] | None = None,
    ) -> None:
        self.row: int = row
        self.col: int = col
        self.value: CellValue | None = value
        self.is_fixed: bool = is_fixed

        self.candidates: set[int]
        if candidates is None:
            self.candidates = set()
        else:
            self.candidates = set(candidates)

    @property
    def coords(self) -> tuple[int, int]:
        """The coordinates of the cell."""
        return (self.row, self.col)

    def __eq__(self, other: Cell) -> bool:
        return self.value == other.value and self.coords == other.coords

    def __hash__(self) -> int:
        return hash(self.coords)

    def clone(self) -> Cell:
        """Creates a clone of the cell."""
        return Cell(
            row=self.row,
            col=self.col,
            value=self.value,
            is_fixed=self.is_fixed,
            candidates=self.candidates,
        )

    def set_value(self, value: CellValue | None) -> None:
        """Sets the value of the cell."""
        self.value = value
        self.candidates.clear()

    def toggle_candidate(self, candidate: int) -> None:
        """Toggles a candidate of the cell."""
        self.value = None

        if candidate in self.candidates:
            self.candidates.remove(candidate)
        else:
            self.candidates.add(candidate)

    def is_sharing_subgrid(self, other: Cell) -> bool:
        """Checks whether the two cells are sharing a subgrid."""
        return self != other and (
            self.row // 3 == other.row // 3 and self.col // 3 == other.col // 3
        )

    def is_neighbour(self, other: Cell) -> bool:
        """Checks whether the two cells are sharing a row, column or subgrid."""
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
        """
        Cells that are invalid.

        Cells that are in the same row, column or subgrid that have the same value.
        """
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
        """Creates a new grid from a string."""
        cells = [
            Cell(
                row=i // 9,
                col=i % 9,
                value=value if (value := int(ch)) else None,  # type: ignore
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

DIFFICULTY_NAME_MAPPING: dict[Difficulty, str] = {
    Difficulty.SUPER_EASY: "Super Easy",
    Difficulty.EASY: "Easy",
    Difficulty.MEDIUM: "Medium",
    Difficulty.HARD: "Hard",
    Difficulty.SUPER_HARD: "Super Hard",
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
        """Starts a new game with a given difficulty."""
        puzzle, solution = get_puzzle_and_solution(difficulty)

        self.grid = Grid.from_str(puzzle)
        self.solution = Grid.from_str(solution)

        self.history.clear()
        self.selected_cell = self.grid[(0, 0)]

    @property
    def is_completed(self) -> bool:
        return self.grid == self.solution

    def move_up(self) -> None:
        """Move the selected cell up."""
        row, col = self.selected_cell.coords
        self.selected_cell = self.grid[((row - 1) % 9, col)]

    def move_down(self) -> None:
        """Move the selected cell down."""
        row, col = self.selected_cell.coords
        self.selected_cell = self.grid[((row + 1) % 9, col)]

    def move_left(self) -> None:
        """Move the selected cell left."""
        row, col = self.selected_cell.coords
        self.selected_cell = self.grid[(row, (col - 1) % 9)]

    def move_right(self) -> None:
        """Move the selected cell right."""
        row, col = self.selected_cell.coords
        self.selected_cell = self.grid[(row, (col + 1) % 9)]

    def undo(self) -> None:
        """Undo a move."""
        cell = self.history.pop()

        self.selected_cell = cell
        self.grid[cell.coords] = cell

    def set_value(self, value: CellValue | None) -> None:
        """
        Sets the value of the selected cell.

        If the selected cell is fixed, does nothing.
        """
        if self.selected_cell.is_fixed:
            return

        self.history.append(self.selected_cell.clone())
        self.selected_cell.set_value(value)

    def toggle_candidate(self, candidate: int) -> None:
        """
        Toggles a candidate of the selected cell.

        If the selected cell is fixed, does nothing.
        """
        if self.selected_cell.is_fixed:
            return

        self.history.append(self.selected_cell.clone())
        self.selected_cell.toggle_candidate(candidate)


class App(Frame):
    def __init__(self, root: Tk) -> None:
        super().__init__(root)

        self.game = Game()


root = Tk()
root.title("Sudoku")

App(root)
root.mainloop()
