from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

from .config import Context, default_mapper, load_config_map, save_config_map, shared_store
from .picker import choose_skills
from .skills import copy_skill, iter_skills, link_skill, remove_path, remove_skill, unique_paths
from .usage import remove_harness_usage, usage_project_paths


def confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


def split_skills_and_harness(values: list[str], ctx: Context) -> tuple[list[str], str]:
    if len(values) > 1 and values[-1] in ctx.mapper:
        return values[:-1], values[-1]
    return values, "default"


def split_target_and_harness(values: list[str], ctx: Context) -> tuple[str, str]:
    if len(values) == 1:
        return values[0], "default"
    if len(values) == 2 and values[-1] in ctx.mapper:
        return values[0], values[1]
    raise SystemExit("Expected: remove <skill-name | skill-folder> [harness]")


def cmd_list(args: argparse.Namespace) -> int:
    ctx = Context.create()
    harnesses = [args.harness] if args.harness else used_project_harnesses(ctx)
    global_harnesses = harnesses
    if args.global_ and not args.project and not args.harness and "default" not in global_harnesses:
        global_harnesses = [*global_harnesses, "default"]
    if args.project and args.global_:
        print("warning: --project and --global together are the default list behavior.", file=sys.stderr)
    printed = False
    for harness in harnesses:
        if args.project and not args.global_:
            printed |= print_level(f"Project ({harness})", ctx.project_skills(harness))
        elif not args.global_ or args.project:
            printed |= print_level(f"Project ({harness})", ctx.project_skills(harness))
            printed |= print_level(f"Global ({harness})", ctx.global_skills(harness))
    if args.global_ and not args.project:
        for harness in global_harnesses:
            printed |= print_level(f"Global ({harness})", ctx.global_skills(harness))
    return 0 if printed or args.quiet else 0


def used_project_harnesses(ctx: Context) -> list[str]:
    used: list[str] = []
    for harness in ctx.mapper:
        prefix = explicit_project_prefix(ctx, harness)
        if prefix is None:
            continue
        path = prefix if prefix.is_absolute() else ctx.cwd / prefix
        if path.exists():
            used.append(harness)
    return used


def explicit_project_prefix(ctx: Context, harness: str) -> Path | None:
    if harness == "default":
        value = ctx.mapper["default"].get("project")
    else:
        value = ctx.mapper.get(harness, {}).get("project")
    if value is None:
        return None
    return Path(value).expanduser()


def print_level(title: str, folder: Path) -> bool:
    skills = iter_skills(folder)
    if not skills:
        return False
    print(f"{title}:")
    for skill in skills:
        print(f"- {skill}")
    return True


def cmd_copy(args: argparse.Namespace) -> int:
    return run_import(args, copy_skill, "copied")


def cmd_link(args: argparse.Namespace) -> int:
    return run_import(args, link_skill, "linked")


def run_import(args: argparse.Namespace, action: Any, label: str) -> int:
    ctx = Context.create()
    skills, harness = split_skills_and_harness(args.values, ctx)
    if not skills:
        skills = choose_skills()
    for skill in skills:
        destination = action(skill, harness, target_project(args), ctx)
        print(f"{label}: {skill} -> {destination}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    ctx = Context.create()
    source = ctx.global_skills(args.src_harness)
    source_skills = iter_skills(source)
    if not source_skills:
        print(f"source has no skills: {source}")
        return 0
    for skill in source_skills:
        if (shared_store() / skill).exists() or (shared_store() / skill).is_symlink():
            continue
        if args.all:
            mirror_skill_to_shared_store(source / skill, skill)
            print(f"added to shared store: {skill} -> {shared_store() / skill}")
        else:
            print(f"warning: source skill not found in shared store: {skill}", file=sys.stderr)

    skills = iter_skills(shared_store())
    if not skills:
        raise SystemExit(f"No skills found in shared store: {shared_store()}")
    action = copy_skill if args.copy else link_skill
    mode = "copy" if args.copy else "link"
    synced = 0
    for skill in skills:
        try:
            target = action(skill, args.dst_harness, target_project(args), ctx)
        except SystemExit as exc:
            if str(exc).startswith("Destination already exists:"):
                print(f"skip existing: {ctx.target_skills(args.dst_harness, target_project(args)) / skill}")
                continue
            raise
        print(f"{mode}: {skill} -> {target}")
        synced += 1
    print(f"synced {synced} skills")
    return 0


def target_project(args: argparse.Namespace) -> bool:
    return not getattr(args, "global_", False)


def mirror_skill_to_shared_store(source: Path, skill: str) -> None:
    target = shared_store() / skill
    if target.exists() or target.is_symlink():
        return
    shared_store().mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, symlinks=True)


def cmd_remove(args: argparse.Namespace) -> int:
    ctx = Context.create()
    target, harness = split_target_and_harness(args.values, ctx)
    removed = remove_skill(target, harness, args.global_, args.link, args.all, ctx)
    for path in removed:
        print(f"removed: {path}")
    return 0


def cmd_completion(args: argparse.Namespace) -> int:
    command = "asb"
    if args.shell == "bash":
        print(f"complete -W 'list copy link remove sync completion config' {command}")
    else:
        print(f"#compdef {command}\n_arguments '1:command:(list copy link remove sync completion config)'")
    return 0


def cmd_config_list(args: argparse.Namespace) -> int:
    config = load_config_map()
    for harness in config:
        print_config_entry(harness, config[harness])
    return 0


def cmd_config_add(args: argparse.Namespace) -> int:
    if args.harness == "default":
        raise SystemExit("Cannot modify the default config.")
    config = load_config_map()
    if args.harness in config and not confirm(f"Config {args.harness!r} exists. Overwrite?"):
        print(f"skip: {args.harness}")
        return 0

    values: dict[str, str] = {}
    if args.project is not None:
        values["project"] = args.project
    if args.global_ is not None:
        values["global"] = args.global_
    config[args.harness] = values
    save_config_map(config)
    print_config_entry(args.harness, values)
    return 0


def cmd_config_remove(args: argparse.Namespace) -> int:
    if args.harness == "default":
        raise SystemExit("Cannot remove the default config.")

    config = load_config_map()
    if args.harness not in config:
        raise SystemExit(f"Unknown config: {args.harness}")

    original = config[args.harness].copy()
    if args.project:
        config[args.harness].pop("project", None)
    elif args.global_:
        config[args.harness].pop("global", None)
    else:
        config.pop(args.harness)
    save_config_map(config)

    deleted_paths = remove_config_skill_paths(args.harness, original, args)
    print(f"removed config: {args.harness}")
    for path in deleted_paths:
        print(f"removed skills: {path}")
    return 0


def print_config_entry(harness: str, values: dict[str, str]) -> None:
    if values:
        fields = "\n\t".join(f"{key} = {value}" for key, value in values.items())
        print(f"{harness}:\n\t{fields}")
    else:
        print(f"{harness}: {{}}")


def remove_config_skill_paths(harness: str, harness_config: dict[str, str], args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    if args.global_:
        paths.append(config_global_skills(harness_config))
    elif args.project:
        paths.extend(config_project_skills(harness_config, project) for project in usage_project_paths(harness))
    else:
        paths.append(config_global_skills(harness_config))
        paths.extend(config_project_skills(harness_config, project) for project in usage_project_paths(harness))

    paths = [path for path in unique_paths(paths) if path.exists() or path.is_symlink()]
    if not paths:
        if not args.project and not args.global_:
            remove_harness_usage(harness)
        return []
    if not args.all and not confirm(f"Delete related skill folders for {harness!r}?"):
        if not args.project and not args.global_:
            remove_harness_usage(harness)
        return []
    removed: list[Path] = []
    for path in paths:
        remove_path(path)
        removed.append(path)
    if not args.project and not args.global_:
        remove_harness_usage(harness)
    return removed


def config_global_skills(config: dict[str, str]) -> Path:
    prefix = config.get("global", default_mapper()["default"]["global"])
    return Path(prefix).expanduser() / "skills"


def config_project_skills(config: dict[str, str], project: Path) -> Path:
    prefix = Path(config.get("project", default_mapper()["default"]["project"])).expanduser()
    if prefix.is_absolute():
        return prefix / "skills"
    return project / prefix / "skills"
