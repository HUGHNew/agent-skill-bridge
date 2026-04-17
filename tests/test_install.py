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


class InstallCommandTests(unittest.TestCase):
    def test_install_runs_skills_add(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                output = StringIO()
                with mock.patch("agent_skill_bridge.commands.subprocess.run") as run, redirect_stdout(output):
                    main(["install", "demo", "-y"])

                run.assert_called_once_with(["npx", "skills", "add", "demo", "-a", "universal", "-g", "-y"], check=True)
                self.assertIn("\033[36m[install]\033[0m\033[1m[global]\033[0m \033[3mdemo\033[0m", output.getvalue())

    def test_install_without_yes_prompts_and_runs_when_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"HOME": home}), mock.patch("agent_skill_bridge.commands.subprocess.run") as run, mock.patch("builtins.input", return_value="y"), redirect_stdout(StringIO()):
                main(["install", "demo"])

            run.assert_called_once_with(["npx", "skills", "add", "demo", "-a", "universal", "-g", "-y"], check=True)

    def test_install_without_yes_skips_when_declined(self) -> None:
        output = StringIO()
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"HOME": home}), mock.patch("agent_skill_bridge.commands.subprocess.run") as run, mock.patch("builtins.input", return_value=""), redirect_stdout(output):
                main(["install", "demo"])

            run.assert_not_called()
        self.assertIn("skip: demo", output.getvalue())


if __name__ == "__main__":
    unittest.main()
