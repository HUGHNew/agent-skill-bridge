from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent_skill_bridge.cli import main


class UpdateCommandTests(unittest.TestCase):
    def test_update_forwards_scope_and_skill_refs(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"HOME": home}), mock.patch("agent_skill_bridge.commands.subprocess.run") as run:
                main(["update", "-g", "-y", "demo", "other"])

        run.assert_called_once_with(
            ["npx", "skills", "update", "-y", "-g", "demo", "other"],
            check=True,
        )

    def test_update_prompts_before_running(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"HOME": home}), mock.patch("agent_skill_bridge.commands.subprocess.run") as run, mock.patch("builtins.input", return_value="y"):
                main(["update", "-p", "demo"])

        run.assert_called_once_with(["npx", "skills", "update", "-y", "-p", "demo"], check=True)

    def test_update_skips_when_confirmation_is_declined(self) -> None:
        output = StringIO()
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"HOME": home}), mock.patch("agent_skill_bridge.commands.subprocess.run") as run, mock.patch("builtins.input", return_value=""), redirect_stdout(output):
                main(["update", "demo"])

        run.assert_not_called()
        self.assertIn("skip: demo", output.getvalue())

    def test_update_without_refs_uses_skill_picker(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"HOME": home}), mock.patch("agent_skill_bridge.commands.choose_skills", return_value=["demo"]), mock.patch("agent_skill_bridge.commands.subprocess.run") as run:
                main(["update", "-g", "-y"])

        run.assert_called_once_with(["npx", "skills", "update", "-y", "-g", "demo"], check=True)

    def test_update_rejects_both_scopes(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stdout(StringIO()):
                main(["update", "-g", "-p", "-y", "demo"])


if __name__ == "__main__":
    unittest.main()
