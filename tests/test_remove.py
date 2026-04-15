from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent_skill_bridge.cli import main
from agent_skill_bridge.config import Context, shared_store
from agent_skill_bridge.skills import copy_skill
from agent_skill_bridge.usage import record_usage


class RemoveCommandTests(unittest.TestCase):
    def test_config_remove_all_deletes_related_skill_paths(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}):
                global_root = Path(config_dir) / "tool"
                project_root = Path(cwd)
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(global_root)])

                (global_root / "skills" / "demo").mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {
                        "project": ".agents",
                        "global": str(Path(config_dir) / "agents"),
                    },
                    "tool": {
                        "project": ".tool",
                        "global": str(global_root),
                    },
                })
                (shared_store() / "demo").mkdir(parents=True)
                copy_skill("demo", "tool", project=True, ctx=ctx)

                with mock.patch("pathlib.Path.cwd", return_value=project_root):
                    with redirect_stdout(StringIO()):
                        main(["config", "remove", "tool", "-a"])

                self.assertFalse((global_root / "skills").exists())
                self.assertFalse((project_root / ".tool" / "skills").exists())

    def test_remove_project_folder_removes_project_skill(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                (shared_store() / "demo").mkdir(parents=True)
                with redirect_stdout(StringIO()):
                    main(["copy", "demo"])
                folder = Path(cwd) / ".agents" / "skills" / "demo"

                with redirect_stdout(StringIO()):
                    main(["remove", str(folder)])

                self.assertFalse(folder.exists())

    def test_remove_global_folder_uses_all_logic(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                (shared_store() / "demo").mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {"project": ".agents", "global": str(Path(config_dir) / "agents")},
                })
                copy_skill("demo", "default", project=True, ctx=ctx)

                with redirect_stdout(StringIO()):
                    main(["remove", str(shared_store() / "demo")])

                self.assertFalse((shared_store() / "demo").exists())
                self.assertFalse((project_root / ".agents" / "skills" / "demo").exists())

    def test_remove_all_keeps_usage_for_missing_recorded_project_path(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            missing_project = Path(cwd) / "missing"
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}):
                (shared_store() / "demo").mkdir(parents=True)
                record_usage("default", missing_project, "demo", "copy")

                with redirect_stdout(StringIO()):
                    main(["remove", "demo", "--all"])

                usage_path = Path(config_dir) / "agent-skill-bridge" / "usage.json"
                usage = json.loads(usage_path.read_text(encoding="utf-8"))
                self.assertEqual(usage["default"]["projects"][str(missing_project.resolve())]["demo"], "copy")

    def test_remove_all_deletes_default_global_and_usage_locations(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(Path(config_dir) / "tool")])
                (shared_store() / "demo").mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {"project": ".agents", "global": str(Path(config_dir) / "agents")},
                    "tool": {"project": ".tool", "global": str(Path(config_dir) / "tool")},
                })
                copy_skill("demo", "tool", project=True, ctx=ctx)

                output = StringIO()
                with redirect_stdout(output):
                    main(["remove", "demo", "--all"])

                self.assertFalse((shared_store() / "demo").exists())
                self.assertFalse((project_root / ".tool" / "skills" / "demo").exists())
                self.assertIn("removed:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
