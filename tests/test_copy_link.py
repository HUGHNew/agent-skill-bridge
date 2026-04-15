from __future__ import annotations

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
from agent_skill_bridge.skills import copy_skill, iter_skills, link_skill


class CopyLinkTests(unittest.TestCase):
    def test_copy_and_link_from_shared_store(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}):
                (shared_store() / "demo").mkdir(parents=True)
                (shared_store() / "demo" / "SKILL.md").write_text("demo\n", encoding="utf-8")
                ctx = Context(Path(cwd), {
                    "default": {
                        "project": ".agents",
                        "global": str(Path(config_dir) / "agents"),
                    },
                    "codex": {
                        "global": str(Path(config_dir) / "codex"),
                    }
                })

                copied = copy_skill("demo", "default", project=True, ctx=ctx)
                linked = link_skill("demo", "codex", project=False, ctx=ctx)

                self.assertTrue((copied / "SKILL.md").exists())
                self.assertTrue(linked.is_symlink())
                self.assertEqual(iter_skills(Path(cwd) / ".agents" / "skills"), ["demo"])

    def test_copy_and_remove_accept_leading_harness(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-g", str(Path(config_dir) / "tool")])
                (shared_store() / "demo").mkdir(parents=True)
                (shared_store() / "demo" / "SKILL.md").write_text("demo\n", encoding="utf-8")

                with redirect_stdout(StringIO()):
                    main(["copy", "tool", "demo", "--global"])
                self.assertTrue((Path(config_dir) / "tool" / "skills" / "demo").exists())

                with redirect_stdout(StringIO()):
                    main(["remove", "tool", "demo", "--global"])
                self.assertFalse((Path(config_dir) / "tool" / "skills" / "demo").exists())

    def test_copy_defaults_to_project_level(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                (shared_store() / "demo").mkdir(parents=True)

                with redirect_stdout(StringIO()):
                    main(["copy", "default", "demo"])

                self.assertTrue((Path(cwd) / ".agents" / "skills" / "demo").exists())
                self.assertFalse((Path(cwd) / ".agents" / "skills" / "demo").is_symlink())

    def test_copy_without_positionals_picks_harness_then_skills(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                (shared_store() / "demo").mkdir(parents=True)
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool"])

                with (
                    mock.patch("agent_skill_bridge.commands.choose_harness", return_value="tool") as harness_picker,
                    mock.patch("agent_skill_bridge.commands.choose_skills", return_value=["demo"]) as skill_picker,
                    redirect_stdout(StringIO()),
                ):
                    main(["copy"])

                harness_picker.assert_called_once()
                self.assertEqual(harness_picker.call_args.kwargs, {"include_default": False})
                skill_picker.assert_called_once()
                self.assertTrue((Path(cwd) / ".tool" / "skills" / "demo").exists())

    def test_copy_requires_leading_harness_when_positionals_exist(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}):
                (shared_store() / "demo").mkdir(parents=True)

                with self.assertRaises(SystemExit) as raised:
                    main(["copy", "demo"])

                self.assertEqual(str(raised.exception), "Unknown harness: demo")


if __name__ == "__main__":
    unittest.main()
