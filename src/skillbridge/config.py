from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_NAME = "skillbridge"


def config_home() -> Path:
    return Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser()


def manager_root() -> Path:
    return config_home() / PROJECT_NAME


def shared_store() -> Path:
    return config_home() / "agents" / "skills"


def default_mapper() -> dict[str, dict[str, str]]:
    return {
        "default": {
            "project": ".agents",
            "global": str(config_home() / "agents"),
        },
        "claude-code": {
            "project": ".claude",
            "global": "~/.claude",
        },
        "codex": {
            "global": "~/.codex",
        },
        "crush": {
            "project": ".crush",
            "global": "~/.crush",
        },
        "deepagents": {
            "global": "~/.deepagents/agent",
        },
    }


def config_map_path() -> Path:
    return manager_root() / "map.json"


def load_config_map() -> dict[str, dict[str, str]]:
    config_path = config_map_path()
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    else:
        raw = default_mapper()

    mapper: dict[str, dict[str, str]] = {}
    for harness, values in raw.items():
        if harness == "default":
            continue
        if not isinstance(values, dict):
            raise SystemExit(f"Invalid mapper entry for {harness!r}: expected object")
        mapper[harness] = {key: str(value) for key, value in values.items()}
    return mapper


def save_config_map(mapper: dict[str, dict[str, str]]) -> None:
    path = config_map_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {name: values for name, values in mapper.items() if name != "default"}
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def load_mapper() -> dict[str, dict[str, str]]:
    defaults = default_mapper()
    mapper = {"default": defaults["default"]}
    mapper.update(load_config_map())
    return mapper


@dataclass(frozen=True)
class Context:
    cwd: Path
    mapper: dict[str, dict[str, str]]

    @classmethod
    def create(cls) -> "Context":
        return cls(cwd=Path.cwd(), mapper=load_mapper())

    def harness_config(self, harness: str) -> dict[str, str]:
        base = self.mapper["default"].copy()
        base.update(self.mapper.get(harness, {}))
        return base

    def project_skills(self, harness: str) -> Path:
        prefix = Path(self.harness_config(harness)["project"]).expanduser()
        if prefix.is_absolute():
            return prefix / "skills"
        return self.cwd / prefix / "skills"

    def global_skills(self, harness: str) -> Path:
        return Path(self.harness_config(harness)["global"]).expanduser() / "skills"

    def target_skills(self, harness: str, project: bool = False) -> Path:
        return self.project_skills(harness) if project else self.global_skills(harness)
