from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent_skill_bridge.cli import main


class ListCommandTests(unittest.TestCase):
    def test_list_accepts_positional_harness(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-g", str(Path(config_dir) / "tool")])
                (Path(config_dir) / "tool" / "skills" / "demo").mkdir(parents=True)

                output = StringIO()
                with redirect_stdout(output):
                    main(["list", "tool", "--global"])
                self.assertIn("Global (tool):", output.getvalue())
                self.assertIn("- demo", output.getvalue())

    def test_list_project_and_global_warns_and_uses_default_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                (Path(cwd) / ".agents" / "skills" / "project-demo").mkdir(parents=True)
                (Path(config_dir) / "agents" / "skills" / "global-demo").mkdir(parents=True)

                output = StringIO()
                error = StringIO()
                with redirect_stdout(output), redirect_stderr(error):
                    main(["list", "default", "--project", "--global"])

                self.assertIn("Project (default):", output.getvalue())
                self.assertIn("- project-demo", output.getvalue())
                self.assertIn("Global (default):", output.getvalue())
                self.assertIn("- global-demo", output.getvalue())
                self.assertIn("warning:", error.getvalue())

    def test_list_without_harness_uses_existing_project_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(Path(config_dir) / "tool")])
                    main(["config", "add", "unused", "-p", ".unused", "-g", str(Path(config_dir) / "unused")])
                (Path(cwd) / ".tool").mkdir()
                (Path(config_dir) / "tool" / "skills" / "tool-global").mkdir(parents=True)
                (Path(config_dir) / "unused" / "skills" / "unused-global").mkdir(parents=True)

                output = StringIO()
                with redirect_stdout(output):
                    main(["list"])

                self.assertIn("Global (tool):", output.getvalue())
                self.assertIn("- tool-global", output.getvalue())
                self.assertNotIn("Global (unused):", output.getvalue())
                self.assertNotIn("- unused-global", output.getvalue())

    def test_list_global_uses_existing_project_prefixes_and_default_global(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(Path(config_dir) / "tool")])
                (Path(cwd) / ".tool").mkdir()
                (Path(config_dir) / "tool" / "skills" / "tool-global").mkdir(parents=True)
                (Path(config_dir) / "agents" / "skills" / "default-global").mkdir(parents=True)

                output = StringIO()
                with redirect_stdout(output):
                    main(["list", "--global"])

                self.assertIn("Global (tool):", output.getvalue())
                self.assertIn("- tool-global", output.getvalue())
                self.assertIn("Global (default):", output.getvalue())
                self.assertIn("- default-global", output.getvalue())


if __name__ == "__main__":
    unittest.main()
