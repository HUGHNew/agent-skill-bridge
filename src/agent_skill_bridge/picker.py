from __future__ import annotations

import curses
from typing import Any

from .config import shared_store
from .skills import iter_skills


def choose_skills() -> list[str]:
    skills = iter_skills(shared_store())
    if not skills:
        raise SystemExit(f"No skills found in shared store: {shared_store()}")
    try:
        return curses.wrapper(skill_picker, skills)
    except curses.error as exc:
        raise SystemExit("Skill picker requires an interactive terminal. Pass skill names as arguments.") from exc


def skill_picker(stdscr: Any, skills: list[str]) -> list[str]:
    curses.curs_set(0)
    stdscr.keypad(True)
    current = 0
    offset = 0
    selected: set[int] = set()

    while True:
        height, width = stdscr.getmaxyx()
        if height < 6 or width < 24:
            raise SystemExit("Terminal is too small for the skill picker.")

        visible_rows = height - 5
        if current < offset:
            offset = current
        elif current >= offset + visible_rows:
            offset = current - visible_rows + 1

        stdscr.erase()
        stdscr.addnstr(0, 0, "Select skills", width - 1, curses.A_BOLD)
        stdscr.addnstr(1, 0, "Arrows/j/k move  Space toggles  Enter accepts  q cancels", width - 1)
        stdscr.hline(2, 0, curses.ACS_HLINE, width)

        for row, index in enumerate(range(offset, min(len(skills), offset + visible_rows)), start=3):
            marker = "[x]" if index in selected else "[ ]"
            line = f"{marker} {skills[index]}"
            attrs = curses.A_REVERSE if index == current else curses.A_NORMAL
            stdscr.addnstr(row, 0, line, width - 1, attrs)

        footer = f"{len(selected)} selected"
        stdscr.hline(height - 2, 0, curses.ACS_HLINE, width)
        stdscr.addnstr(height - 1, 0, footer, width - 1)
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            current = max(0, current - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            current = min(len(skills) - 1, current + 1)
        elif key in (ord(" "),):
            if current in selected:
                selected.remove(current)
            else:
                selected.add(current)
        elif key in (curses.KEY_ENTER, 10, 13):
            if not selected:
                selected.add(current)
            return [skill for index, skill in enumerate(skills) if index in selected]
        elif key in (27, ord("q")):
            raise SystemExit("Cancelled.")
