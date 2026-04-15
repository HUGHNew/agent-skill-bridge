from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import manager_root


def usage_path() -> Path:
    return manager_root() / "asb-usage.json"


def load_usage() -> dict[str, Any]:
    path = usage_path()
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_usage(usage: dict[str, Any]) -> None:
    path = usage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(usage, fh, indent=2)
        fh.write("\n")


def project_key(path: Path) -> str:
    return str(path.resolve())


def record_usage(harness: str, project: Path, skill: str, mode: str) -> None:
    usage = load_usage()
    harness_usage = usage.setdefault(harness, {})
    projects = harness_usage.setdefault("projects", {})
    skills = projects.setdefault(project_key(project), {})
    skills[skill] = mode
    save_usage(usage)


def record_global_usage(harness: str, skill: str, mode: str) -> None:
    usage = load_usage()
    harness_usage = usage.setdefault(harness, {})
    globals_ = harness_usage.setdefault("globals", {})
    skills = globals_.setdefault(harness, {})
    skills[skill] = mode
    save_usage(usage)


def remove_usage(harness: str, project: Path, skill: str | None = None) -> None:
    usage = load_usage()
    harness_usage = usage.get(harness, {})
    projects = harness_usage.get("projects", {})
    skills = projects.get(project_key(project))
    if not isinstance(skills, dict):
        return
    if skill is None:
        skills.clear()
    else:
        skills.pop(skill, None)
    if not skills:
        projects.pop(project_key(project), None)
    if not projects:
        harness_usage.pop("projects", None)
    if harness in usage and not harness_usage:
        usage.pop(harness, None)
    save_usage(usage)


def remove_global_usage(harness: str, skill: str | None = None) -> None:
    usage = load_usage()
    harness_usage = usage.get(harness, {})
    globals_ = harness_usage.get("globals", {})
    skills = globals_.get(harness)
    if not isinstance(skills, dict):
        return
    if skill is None:
        skills.clear()
    else:
        skills.pop(skill, None)
    if not skills:
        globals_.pop(harness, None)
    if not globals_:
        harness_usage.pop("globals", None)
    if harness in usage and not harness_usage:
        usage.pop(harness, None)
    save_usage(usage)


def find_skill_usage(skill: str) -> list[tuple[str, Path]]:
    matches: list[tuple[str, Path]] = []
    for harness, harness_usage in load_usage().items():
        projects = harness_usage.get("projects", {})
        if not isinstance(projects, dict):
            continue
        for project, skills in projects.items():
            if not isinstance(skills, dict) or skill not in skills:
                continue
            matches.append((harness, Path(project)))
    return matches


def find_skill_global_usage(skill: str) -> list[str]:
    matches: list[str] = []
    for harness, harness_usage in load_usage().items():
        globals_ = harness_usage.get("globals", {})
        if not isinstance(globals_, dict):
            continue
        skills = globals_.get(harness, {})
        if isinstance(skills, dict) and skill in skills:
            matches.append(harness)
    return matches


def remove_skill_usage_entries(skill: str, entries: list[tuple[str, Path]]) -> None:
    usage = load_usage()
    for harness, project_path in entries:
        harness_usage = usage.get(harness, {})
        projects = harness_usage.get("projects", {})
        if not isinstance(projects, dict):
            continue
        project = project_key(project_path)
        skills = projects.get(project)
        if not isinstance(skills, dict) or skill not in skills:
            continue
        skills.pop(skill, None)
        if not skills:
            projects.pop(project, None)
        if not projects:
            harness_usage.pop("projects", None)
        if harness in usage and not harness_usage:
            usage.pop(harness, None)
    save_usage(usage)


def remove_skill_global_usage_entries(skill: str, entries: list[str]) -> None:
    usage = load_usage()
    for harness in entries:
        harness_usage = usage.get(harness, {})
        globals_ = harness_usage.get("globals", {})
        if not isinstance(globals_, dict):
            continue
        skills = globals_.get(harness)
        if not isinstance(skills, dict) or skill not in skills:
            continue
        skills.pop(skill, None)
        if not skills:
            globals_.pop(harness, None)
        if not globals_ and not harness_usage.get("projects"):
            usage.pop(harness, None)
    save_usage(usage)


def remove_skill_usage_everywhere(skill: str) -> list[tuple[str, Path]]:
    entries = find_skill_usage(skill)
    global_entries = find_skill_global_usage(skill)
    remove_skill_usage_entries(skill, entries)
    remove_skill_global_usage_entries(skill, global_entries)
    return entries


def remove_harness_usage(harness: str) -> None:
    usage = load_usage()
    if harness in usage:
        usage.pop(harness, None)
        save_usage(usage)


def usage_project_paths(harness: str) -> list[Path]:
    projects = load_usage().get(harness, {}).get("projects", {})
    if not isinstance(projects, dict):
        return []
    return [Path(path) for path in projects if isinstance(path, str)]
