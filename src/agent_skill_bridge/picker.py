from __future__ import annotations

from pathlib import Path

from questionary import checkbox, select

from .config import Context, shared_store
from .skills import iter_skills

MASK = " | "

def mask_off(content: str):
    if MASK in content:
        return content[:content.index(MASK)]
    return content

def choose_harness(ctx: Context, include_default: bool = True) -> str:
    harnesses = [
        harness for harness in ctx.mapper if include_default or harness != "default"
    ]
    if not harnesses:
        raise SystemExit("No harness configs found.")
    return choose_one("Select harness", harnesses)


def choose_skills(
    folder: Path | None = None,
    skill_hint: dict[str, int] = {},
) -> list[str]:
    source = folder or shared_store()
    skills = iter_skills(source)
    if not skills:
        raise SystemExit(f"No skills found: {source}")

    labeled: list[str] = []
    for skill in skills:
        status = skill_hint.get(skill, 0) # independent
        if status == 1: # link
            labeled.append(f"{skill} | [linked]")
        elif status == 2: # copy
            labeled.append(f"{skill} | [copied]")
        else:
            labeled.append(skill)

    return choose_many("Select skills", labeled)


def choose_one(title: str, options: list[str]) -> str:
    selected = select(
        title,
        choices=options,
        instruction="\n Arrow: move | Enter: confirm",
        pointer=">",
    ).ask()
    if selected is None:
        raise SystemExit("Cancelled.")
    return selected


def choose_many(title: str, options: list[str]) -> list[str]:
    selected = checkbox(
        title,
        choices=options,
        instruction="\n Arrow: move | Space: select/cancel | Enter: confirm",
        pointer=">",
    ).ask()
    if selected is None:
        raise SystemExit("Cancelled.")
    if not selected:
        raise SystemExit("No skills selected.")
    return [mask_off(s) for s in selected]
