from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from copy import deepcopy
from enum import Enum, auto
from functools import partial
from pathlib import Path
from random import choice
from tkinter import (
    BOTH,
    BOTTOM,
    LEFT,
    NSEW,
    TOP,
    Button,
    Canvas,
    Event,
    Frame,
    Misc,
    PhotoImage,
    Tk,
    Toplevel,
    X,
)
from typing import Literal


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

FONT_FAMILY = "Fira Sans"

PADDING = 20
PADDING_SMALL = 5

CELL_SIZE = 60
CELL_SIZE_SMALL = CELL_SIZE // 3

WIDTH = 9 * CELL_SIZE
HEIGHT = 9 * CELL_SIZE

BLACK = "#344861"
GREY = "#BEC6D4"
WHITE = "#FFFFFF"

BLUE = "#0072E3"
ACTIVE_BLUE = "#0065C8"

WHITE_BLUE = "#EAEEF4"
ACTIVE_WHITE_BLUE = "#DCE3ED"

LIGHT_BLUE = "#BBDEFB"
PALE_LIGHT_BLUE = "#E2EBF3"
OTHER_LIGHT_BLUE = "#C3D7EA"

RED = "#E55C6C"
LIGHT_RED = "#F7CFD6"
ACTIVE_LIGHT_RED = "#FABEC9"

CLEAR_KEYS = frozenset(["BackSpace", "Delete"])
UP_KEYS = frozenset(["Up", "w"])
LEFT_KEYS = frozenset(["Left", "a"])
DOWN_KEYS = frozenset(["Down", "s"])
RIGHT_KEYS = frozenset(["Right", "d"])

DATA_PATH = Path(__file__).parent.parent / "data"
ICON_PATH = Path(__file__).parent.parent / "assets" / "icons"


CellValue = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]


class Cell:
    def __init__(
        self,
        row: int,
        col: int,
        value: CellValue | None,
        is_fixed: bool,
        candidates: Iterable[CellValue] | None = None,
    ) -> None:
        self.row: int = row
        self.col: int = col
        self.value: CellValue | None = value
        self.is_fixed: bool = is_fixed

        self.candidates: set[CellValue]
        if candidates is None:
            self.candidates = set()
        else:
            self.candidates = set(candidates)

    def __eq__(self, other: Cell) -> bool:
        return self.value == other.value and self.coords == other.coords

    def __hash__(self) -> int:
        return hash(self.coords)

    @property
    def coords(self) -> tuple[int, int]:
        """The coordinates of the cell."""
        return (self.row, self.col)

    def set_value(self, value: CellValue | None) -> None:
        """Sets the value of the cell."""
        assert not self.is_fixed

        self.value = value
        self.candidates.clear()

    def toggle_candidate(self, candidate: CellValue) -> None:
        """Toggles a candidate of the cell."""
        assert not self.is_fixed

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
        assert len(cells) == 81
        assert all([cell.coords == (i // 9, i % 9) for i, cell in enumerate(cells)])

        self._cells = cells

    def __eq__(self, other: Grid) -> bool:
        return self._cells == other._cells

    def __iter__(self) -> Iterator[Cell]:
        return iter(self._cells)

    def __getitem__(self, coords: tuple[int, int]) -> Cell:
        row, col = coords
        return self._cells[row * 9 + col]

    def __setitem__(self, coords: tuple[int, int], cell: Cell) -> None:
        assert coords == cell.coords

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


def get_puzzle_and_solution(difficulty: Difficulty) -> tuple[str, str]:
    """Gets a random puzzle and its corresponding solution for a given difficulty."""
    csv_path = (DATA_PATH / DIFFICULTY_FILE_MAPPING[difficulty]).with_suffix(".csv")
    with open(csv_path, newline="") as csv_file:
        reader = csv.reader(csv_file)
        puzzle, solution = choice(tuple(reader))

    return puzzle, solution


class Board(Canvas):
    def __init__(self, master: Misc) -> None:
        super().__init__(
            master,
            width=WIDTH,
            height=HEIGHT,
            background=WHITE,
            highlightbackground=BLACK,
            highlightthickness=2,
        )

        self.history: list[Cell] = []

    def start(self, difficulty: Difficulty) -> None:
        """Starts a new game with a given difficulty."""
        puzzle, solution = get_puzzle_and_solution(difficulty)

        self.grid = Grid.from_str(puzzle)
        self.solution = Grid.from_str(solution)

        self.history.clear()
        self.selected_cell = self.grid[(0, 0)]

        self.draw()

    @property
    def is_completed(self) -> bool:
        """Checks if the puzzle is completed."""
        return self.grid == self.solution

    def move(self, coords: tuple[int, int]) -> None:
        """Moves the selected cell to the given coordinates."""
        if self.is_completed:
            return

        row, col = coords
        self.selected_cell = self.grid[(row % 9, col % 9)]

        self.draw()

    def move_up(self) -> None:
        """Move the selected cell up."""
        row, col = self.selected_cell.coords
        self.move((row - 1, col))

    def move_down(self) -> None:
        """Move the selected cell down."""
        row, col = self.selected_cell.coords
        self.move((row + 1, col))

    def move_left(self) -> None:
        """Move the selected cell left."""
        row, col = self.selected_cell.coords
        self.move((row, col - 1))

    def move_right(self) -> None:
        """Move the selected cell right."""
        row, col = self.selected_cell.coords
        self.move((row, col + 1))

    def set_value(self, value: CellValue | None) -> None:
        """Sets the value of the selected cell."""
        if self.selected_cell.is_fixed or self.is_completed:
            return

        self.history.append(deepcopy(self.selected_cell))
        self.selected_cell.set_value(value)

        self.draw()

    def toggle_candidate(self, candidate: CellValue) -> None:
        """Toggles a candidate of the selected cell."""
        if self.selected_cell.is_fixed or self.is_completed:
            return

        self.history.append(deepcopy(self.selected_cell))
        self.selected_cell.toggle_candidate(candidate)

        self.draw()

    def undo(self) -> None:
        """Undoes a move."""
        if not self.history or self.is_completed:
            return

        cell = self.history.pop()

        self.selected_cell = cell
        self.grid[cell.coords] = cell

        self.draw()

    def hint(self) -> None:
        """Hints the selected cell."""
        if self.selected_cell.is_fixed or self.is_completed:
            return

        coords = self.selected_cell.coords
        cell = self.solution[coords]

        self.selected_cell = cell
        self.grid[coords] = cell

        # Remove all cells that have the same coords from history
        self.history = [cell for cell in self.history if cell.coords != coords]

        self.draw()

    def draw(self) -> None:
        self.delete("all")

        self.draw_cells()
        self.draw_grid()

        if self.is_completed:
            self.draw_completed()

    def draw_grid(self) -> None:
        # Draw the rows
        for i in range(1, 9):
            colour, width = (BLACK, 2) if i % 3 == 0 else (GREY, 1)

            x0 = 0
            y0 = i * CELL_SIZE
            x1 = WIDTH
            y1 = i * CELL_SIZE

            self.create_line(x0, y0, x1, y1, fill=colour, width=width)

        # Draw the columns
        for i in range(1, 9):
            colour, width = (BLACK, 2) if i % 3 == 0 else (GREY, 1)

            x0 = i * CELL_SIZE
            y0 = 0
            x1 = i * CELL_SIZE
            y1 = HEIGHT

            self.create_line(x0, y0, x1, y1, fill=colour, width=width)

    def draw_cells(self) -> None:
        selected_cell = self.selected_cell
        invalid_cells = self.grid.invalid_cells

        for cell in self.grid:
            x0 = cell.col * CELL_SIZE
            y0 = cell.row * CELL_SIZE
            x1 = x0 + CELL_SIZE
            y1 = y0 + CELL_SIZE

            if selected_cell == cell:
                self.create_rectangle(x0, y0, x1, y1, fill=LIGHT_BLUE, width=0)
            elif cell in invalid_cells:
                self.create_rectangle(x0, y0, x1, y1, fill=LIGHT_RED, width=0)
            elif selected_cell.is_neighbour(cell):
                self.create_rectangle(x0, y0, x1, y1, fill=PALE_LIGHT_BLUE, width=0)
            elif selected_cell.value is not None and selected_cell.value == cell.value:
                self.create_rectangle(x0, y0, x1, y1, fill=OTHER_LIGHT_BLUE, width=0)

            if cell.value is not None:
                colour = BLACK if cell.is_fixed else BLUE

                x = x0 + 0.5 * CELL_SIZE
                y = y0 + 0.5 * CELL_SIZE

                self.create_text(
                    x,
                    y,
                    fill=colour,
                    text=cell.value,
                    font=(FONT_FAMILY, 28),
                )

            elif cell.candidates:
                for candidate in cell.candidates:
                    row = (candidate - 1) // 3
                    col = (candidate - 1) % 3

                    x = (
                        x0
                        + (col * CELL_SIZE_SMALL + 0.5 * CELL_SIZE_SMALL)
                        - (col - 1) * (PADDING_SMALL // 2)
                    )

                    y = (
                        y0
                        + (row * CELL_SIZE_SMALL + 0.5 * CELL_SIZE_SMALL)
                        - (row - 1) * (PADDING_SMALL // 2)
                    )

                    self.create_text(
                        x,
                        y,
                        fill=BLACK,
                        text=candidate,
                        font=(FONT_FAMILY, 10),
                    )

    def draw_completed(self) -> None:
        x0 = CELL_SIZE * 2
        y0 = CELL_SIZE * 2
        x1 = CELL_SIZE * 7
        y1 = CELL_SIZE * 7

        self.create_oval(x0, y0, x1, y1, fill=BLUE, width=0)

        x = WIDTH // 2
        y = HEIGHT // 2

        self.create_text(x, y, text="Completed!", fill=WHITE, font=(FONT_FAMILY, 32))


class WhiteBlueButton(Button):
    def __init__(self, master: Misc, text: str, font_size: int) -> None:
        super().__init__(
            master,
            text=text,
            height=2,
            font=(FONT_FAMILY, font_size),
            background=WHITE_BLUE,
            foreground=BLUE,
            activebackground=ACTIVE_WHITE_BLUE,
            activeforeground=BLUE,
        )


class BlueWhiteButton(Button):
    def __init__(self, master: Misc, text: str, font_size: int) -> None:
        super().__init__(
            master,
            text=text,
            font=(FONT_FAMILY, font_size),
            height=2,
            background=BLUE,
            foreground=WHITE,
            activebackground=ACTIVE_BLUE,
            activeforeground=WHITE,
        )


class IconButton(Button):
    def __init__(self, master: Misc, icon: str) -> None:
        super().__init__(
            master,
            height=64,
            background=WHITE_BLUE,
            activebackground=ACTIVE_WHITE_BLUE,
        )

        self.icon = PhotoImage(file=(ICON_PATH / icon).with_suffix(".png"))
        self.configure(image=self.icon)


class ControlMenu(Frame):
    def __init__(self, master: Misc) -> None:
        super().__init__(master, background=WHITE)

        for i in range(2):
            self.rowconfigure(i, weight=1)

        for i in range(4):
            self.columnconfigure(i, weight=1)

        self.new_game_button = BlueWhiteButton(self, text="New Game", font_size=16)
        self.new_game_button.grid(
            row=0,
            column=0,
            columnspan=4,
            sticky=NSEW,
            pady=(0, PADDING),
        )

        self.undo_button = IconButton(self, icon="undo")
        self.undo_button.grid(row=1, column=0, sticky=NSEW, padx=(0, PADDING))

        self.erase_button = IconButton(self, icon="erase")
        self.erase_button.grid(column=1, row=1, sticky=NSEW, padx=(0, PADDING))

        self.notes_button = IconButton(self, icon="notes")
        self.notes_button.grid(column=2, row=1, sticky=NSEW, padx=(0, PADDING))

        self.hint_button = IconButton(self, icon="hint")
        self.hint_button.grid(column=3, row=1, sticky=NSEW)


class NumberPad(Frame):
    def __init__(self, master: Misc) -> None:
        super().__init__(master, background=WHITE)

        self.buttons: list[Button] = []

        for i in range(3):
            self.rowconfigure(i, weight=1)

        for i in range(3):
            self.columnconfigure(i, weight=1)

        for i in range(9):
            button = WhiteBlueButton(self, text=str(i + 1), font_size=60)

            row = i // 3
            col = i % 3

            padx = (PADDING_SMALL if col != 0 else 0, PADDING_SMALL if col != 2 else 0)
            pady = (PADDING_SMALL if row != 0 else 0, PADDING_SMALL if row != 2 else 0)

            button.grid(row=row, column=col, sticky=NSEW, padx=padx, pady=pady)

            self.buttons.append(button)


class NewGameDialog(Toplevel):
    def __init__(self, master: Tk) -> None:
        super().__init__(master, background=WHITE, padx=PADDING, pady=PADDING)

        self.difficulty: Difficulty | None = None

        self.title("New Game")
        self.geometry("300x360")
        self.resizable(False, False)

        for difficulty in Difficulty:
            handle_button_pressed = partial(self.set_difficulty, difficulty)

            button = WhiteBlueButton(
                self,
                text=DIFFICULTY_NAME_MAPPING[difficulty],
                font_size=12,
            )

            button.pack(side=TOP, fill=X, pady=PADDING_SMALL)
            button.configure(command=handle_button_pressed)

        self.protocol("WM_DELETE_WINDOW", self.dismiss)

        self.transient(master)
        self.wait_visibility()
        self.grab_set()
        self.wait_window()

    def set_difficulty(self, difficulty: Difficulty) -> None:
        self.difficulty = difficulty
        self.dismiss()

    def dismiss(self) -> None:
        self.grab_release()
        self.destroy()


class App(Frame):
    def __init__(self, master: Tk) -> None:
        super().__init__(master, background=WHITE)

        self.pack(fill=BOTH, expand=True)

        self.board = Board(self)
        self.board.focus_set()
        self.board.pack(fill=BOTH, side=LEFT, padx=PADDING, pady=PADDING)

        self.control_menu = ControlMenu(self)
        self.control_menu.pack(fill=BOTH, side=TOP, padx=(0, PADDING), pady=PADDING)

        self.number_pad = NumberPad(self)
        self.number_pad.pack(
            fill=BOTH,
            side=BOTTOM,
            padx=(0, PADDING),
            pady=(0, PADDING),
        )

        self.board.bind("<Key>", self.handle_key_pressed)
        self.board.bind("<Button-1>", self.handle_cell_clicked)

        self.control_menu.new_game_button.configure(command=self.start)
        self.control_menu.undo_button.configure(command=self.board.undo)
        self.control_menu.hint_button.configure(command=self.board.hint)
        self.control_menu.notes_button.configure(command=self.toggle_notes_entry_mode)

        handle_erase_button_pressed = partial(self.update_board, None)
        self.control_menu.erase_button.configure(command=handle_erase_button_pressed)

        for i, button in enumerate(self.number_pad.buttons, 1):
            handle_button_pressed = partial(self.update_board, i)  # type: ignore
            button.configure(command=handle_button_pressed)

        self.is_notes_entry_mode = False
        self.start(Difficulty.MEDIUM)

    def start(self, difficulty: Difficulty | None = None) -> None:
        """Stars a new game with a given difficulty."""
        if difficulty is None:
            dialog = NewGameDialog(self.master)  # type: ignore
            difficulty = dialog.difficulty

        if difficulty is None:
            return

        title = f"Sudoku ({DIFFICULTY_NAME_MAPPING[difficulty]})"
        self.master.title(title)  # type: ignore

        self.board.start(difficulty)

    def toggle_notes_entry_mode(self) -> None:
        """Toggles the notes entry mode."""
        self.is_notes_entry_mode = not self.is_notes_entry_mode

        colour = LIGHT_RED if self.is_notes_entry_mode else WHITE_BLUE
        active_colour = (
            ACTIVE_LIGHT_RED if self.is_notes_entry_mode else ACTIVE_WHITE_BLUE
        )

        self.control_menu.notes_button.configure(
            background=colour,
            activebackground=active_colour,
        )

    def update_board(self, value: CellValue | None) -> None:
        if self.is_notes_entry_mode:
            assert value is not None
            self.board.toggle_candidate(value)
        else:
            self.board.set_value(value)

    def handle_cell_clicked(self, event: Event) -> None:
        if 0 <= event.x <= WIDTH and 0 <= event.y <= HEIGHT:
            row, col = event.y // CELL_SIZE, event.x // CELL_SIZE
            self.board.move((row, col))

    def handle_key_pressed(self, event: Event) -> None:
        if event.char.isdigit() and 1 <= (value := int(event.char)) <= 9:
            self.update_board(value)  # type: ignore
        elif event.keysym in CLEAR_KEYS:
            self.update_board(None)
        elif event.keysym in UP_KEYS:
            self.board.move_up()
        elif event.keysym in DOWN_KEYS:
            self.board.move_down()
        elif event.keysym in LEFT_KEYS:
            self.board.move_left()
        elif event.keysym in RIGHT_KEYS:
            self.board.move_right()


root = Tk()

root.configure(background=WHITE)
root.resizable(False, False)
root.geometry(f"{WIDTH + 2 * PADDING + 360}x{HEIGHT + 2 * PADDING}")

App(root)

root.mainloop()
