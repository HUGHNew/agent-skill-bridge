from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from .config import Context, shared_store
from .usage import (
    find_skill_global_usage,
    find_skill_usage,
    record_global_usage,
    record_usage,
    remove_global_usage,
    remove_skill_global_usage_entries,
    remove_skill_usage_entries,
    remove_usage,
)


def iter_skills(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    return [entry.name for entry in folder.iterdir() if entry.is_dir() or entry.is_symlink()]


def ensure_skill_source(skill: str) -> Path:
    source = shared_store() / skill
    if not source.exists():
        raise SystemExit(f"Skill not found in shared store: {source}")
    if not source.is_dir():
        raise SystemExit(f"Skill is not a directory: {source}")
    return source


def ensure_available_destination(destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise SystemExit(f"Destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)


def copy_skill(skill: str, harness: str, project: bool, ctx: Context) -> Path:
    source = ensure_skill_source(skill)
    destination = ctx.target_skills(harness, project) / skill
    if source.resolve() == destination.resolve():
        return destination
    ensure_available_destination(destination)
    shutil.copytree(source, destination, symlinks=True)
    if project:
        record_usage(harness, ctx.cwd, skill, "copy")
    else:
        record_global_usage(harness, skill, "copy")
    return destination


def link_skill(skill: str, harness: str, project: bool, ctx: Context) -> Path:
    source = ensure_skill_source(skill)
    destination = ctx.target_skills(harness, project) / skill
    if source.resolve() == destination.resolve():
        return destination
    ensure_available_destination(destination)
    destination.symlink_to(source, target_is_directory=True)
    if project:
        record_usage(harness, ctx.cwd, skill, "link")
    else:
        record_global_usage(harness, skill, "link")
    return destination


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def remove_skill(target: str, harness: str, global_only: bool, linked: bool, all_known: bool, ctx: Context) -> list[Path]:
    if all_known:
        if is_path_target(target):
            raise SystemExit("remove --all requires a skill name, not a skill folder.")
        return remove_skill_everywhere(target, ctx)

    target_path = Path(target).expanduser()
    if is_path_target(target):
        if not target_path.is_absolute():
            target_path = (ctx.cwd / target_path).resolve()
        if not target_path.exists() and not target_path.is_symlink():
            raise SystemExit(f"Unknown skill folder: {target}")
        detected = detect_skill_folder(target_path, ctx)
        if detected is None:
            raise SystemExit(f"Unknown skill folder level: {target}")
        skill_harness, skill_global, skill = detected
        if skill_global:
            return remove_skill_everywhere(skill, ctx)
        harness = skill_harness
        global_only = False
    else:
        skill = target

    candidates: list[Path] = []
    if global_only:
        candidates.append(ctx.global_skills(harness) / skill)
    else:
        candidates.append(ctx.project_skills(harness) / skill)

    removed: list[Path] = []
    for candidate in unique_paths(candidates):
        if candidate.exists() or candidate.is_symlink():
            if linked and candidate.is_symlink():
                linked_target = candidate.resolve()
                remove_path(candidate)
                if linked_target.exists() and shared_store().resolve() in linked_target.parents:
                    remove_path(linked_target)
                    removed.append(linked_target)
            else:
                remove_path(candidate)
            removed.append(candidate)

    if not removed:
        raise SystemExit(f"Unknown skill: {target}")

    if not global_only:
        remove_usage(harness, ctx.cwd, skill)
        cleanup_project_prefix(harness, ctx)
    else:
        remove_global_usage(harness, skill)
    return removed


def remove_skill_everywhere(skill: str, ctx: Context) -> list[Path]:
    usage_entries = find_skill_usage(skill)
    global_usage_entries = find_skill_global_usage(skill)
    candidates = [ctx.global_skills("default") / skill]
    candidates.extend(ctx.global_skills(harness) / skill for harness in global_usage_entries)
    removed_usage_entries: list[tuple[str, Path]] = []
    removed_global_usage_entries: list[str] = []
    for harness, project in usage_entries:
        candidates.append(project_skill_path(ctx, harness, project) / skill)

    removed: list[Path] = []
    for candidate in unique_paths(candidates):
        if candidate.exists() or candidate.is_symlink():
            remove_path(candidate)
            removed.append(candidate)
            removed_usage_entries.extend(
                (harness, project)
                for harness, project in usage_entries
                if candidate == project_skill_path(ctx, harness, project) / skill
            )
            removed_global_usage_entries.extend(
                harness
                for harness in global_usage_entries
                if candidate == ctx.global_skills(harness) / skill
            )
    if not removed:
        raise SystemExit(f"Unknown skill: {skill}")
    remove_skill_usage_entries(skill, removed_usage_entries)
    remove_skill_global_usage_entries(skill, removed_global_usage_entries)
    for harness, project in removed_usage_entries:
        cleanup_project_prefix(harness, ctx, project)
    return removed


def project_skill_path(ctx: Context, harness: str, project: Path) -> Path:
    prefix = Path(ctx.harness_config(harness)["project"]).expanduser()
    if prefix.is_absolute():
        return prefix / "skills"
    return project / prefix / "skills"


def project_prefix_path(ctx: Context, harness: str, project: Path | None = None) -> Path:
    prefix = Path(ctx.harness_config(harness)["project"]).expanduser()
    if prefix.is_absolute():
        return prefix
    return (project or ctx.cwd) / prefix


def cleanup_project_prefix(harness: str, ctx: Context, project: Path | None = None) -> None:
    prefix = project_prefix_path(ctx, harness, project)
    if project is None and prefix.resolve() == ctx.cwd.resolve():
        return
    if project is not None and prefix.resolve() == project.resolve():
        return
    skills = prefix / "skills"
    if not prefix.is_dir() or not skills.is_dir():
        return
    if any(skills.iterdir()):
        return
    if any(entry.name != "skills" for entry in prefix.iterdir()):
        return
    shutil.rmtree(prefix)


def is_path_target(target: str) -> bool:
    return Path(target).expanduser().is_absolute() or "/" in target or target.startswith(".")


def detect_skill_folder(path: Path, ctx: Context) -> tuple[str, bool, str] | None:
    for harness in ctx.mapper:
        global_root = ctx.global_skills(harness)
        if path.parent == global_root:
            return harness, True, path.name
        project_root = ctx.project_skills(harness)
        if path.parent == project_root:
            return harness, False, path.name
    return None


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique
