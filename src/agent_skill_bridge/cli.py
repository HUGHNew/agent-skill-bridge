from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from agent_skill_bridge.commands import (  # type: ignore[no-redef]
        cmd_completion,
        cmd_config_add,
        cmd_config_list,
        cmd_config_remove,
        cmd_copy,
        cmd_link,
        cmd_list,
        cmd_remove,
        cmd_sync,
        cmd_usage,
    )
else:
    from .commands import (
        cmd_completion,
        cmd_config_add,
        cmd_config_list,
        cmd_config_remove,
        cmd_copy,
        cmd_link,
        cmd_list,
        cmd_remove,
        cmd_sync,
        cmd_usage,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list skills")
    list_parser.add_argument("harness", nargs="?", help="optional harness name")
    list_parser.add_argument("-g", "--global", dest="global_", action="store_true", help="list harness global skills")
    list_parser.add_argument("-p", "--project", action="store_true", help="list project skills")
    list_parser.add_argument("-q", "--quiet", action="store_true", help="do not print empty levels")
    list_parser.set_defaults(func=cmd_list)

    for name, func in (("copy", cmd_copy), ("link", cmd_link)):
        import_parser = subparsers.add_parser(name, help=f"{name} skills from the shared store")
        import_parser.add_argument("values", nargs="*", help="harness name followed by optional skill names")
        import_parser.add_argument("-p", "--project", action="store_true", help="write into project-level harness config")
        import_parser.add_argument("-g", "--global", dest="global_", action="store_true", help="write into harness global config")
        import_parser.set_defaults(func=func)

    remove_parser = subparsers.add_parser("remove", help="remove a skill")
    remove_parser.add_argument("values", nargs="*", help="harness name followed by optional skill names or folders")
    remove_parser.add_argument("-g", "--global", dest="global_", action="store_true", help="remove from harness global skills")
    remove_parser.add_argument("-l", "--link", action="store_true", help="remove linked shared-store skill too")
    remove_parser.add_argument("-a", "--all", action="store_true", help="remove from default global and recorded project usage")
    remove_parser.set_defaults(func=cmd_remove)

    sync_parser = subparsers.add_parser("sync", help="sync skills between harnesses")
    sync_parser.add_argument("src_harness")
    sync_parser.add_argument("dst_harness")
    sync_parser.add_argument("-c", "--copy", action="store_true", help="sync in copy mode")
    sync_parser.add_argument("-a", "--all", action="store_true", help="copy source-only skills into the shared store")
    sync_parser.add_argument("-p", "--project", action="store_true", help="sync into destination project path")
    sync_parser.add_argument("-g", "--global", dest="global_", action="store_true", help="sync into destination global path")
    sync_parser.set_defaults(func=cmd_sync)

    completion_parser = subparsers.add_parser("completion", help="print shell completion")
    completion_parser.add_argument("shell", choices=["bash", "zsh"])
    completion_parser.set_defaults(func=cmd_completion)

    usage_parser = subparsers.add_parser("usage", help="print recorded skill usage")
    usage_parser.set_defaults(func=cmd_usage)

    config_parser = subparsers.add_parser("config", help="manage harness configs")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)

    config_list_parser = config_subparsers.add_parser("list", help="list harness configs")
    config_list_parser.set_defaults(func=cmd_config_list)

    config_add_parser = config_subparsers.add_parser("add", help="add or replace a harness config")
    config_add_parser.add_argument("harness")
    config_add_parser.add_argument("-p", "--project", help="project config prefix")
    config_add_parser.add_argument("-g", "--global", dest="global_", help="global config prefix")
    config_add_parser.set_defaults(func=cmd_config_add)

    config_remove_parser = config_subparsers.add_parser("remove", help="remove a harness config or field")
    config_remove_parser.add_argument("harness")
    config_remove_parser.add_argument("-p", "--project", action="store_true", help="remove only the project prefix")
    config_remove_parser.add_argument("-g", "--global", dest="global_", action="store_true", help="remove only the global prefix")
    config_remove_parser.add_argument("-a", "--all", action="store_true", help="also delete related skill folders")
    config_remove_parser.set_defaults(func=cmd_config_remove)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "config" and args.config_command == "remove" and args.global_ and args.project:
        parser.error("--global and --project cannot be used together")
    if args.command in {"copy", "link", "sync"} and getattr(args, "global_", False) and getattr(args, "project", False):
        parser.error("--global and --project cannot be used together")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
