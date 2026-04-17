from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent_skill_bridge.config import Context, shared_store
from agent_skill_bridge.picker import choose_harness, choose_skills


class PickerTests(unittest.TestCase):
    def test_choose_skills_uses_space_then_enter(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                (shared_store() / "demo").mkdir(parents=True)
                with mock.patch("agent_skill_bridge.picker.checkbox") as checkbox:
                    checkbox.return_value.ask.return_value = ["demo"]
                    self.assertEqual(choose_skills(), ["demo"])
                checkbox.assert_called_once()

    def test_choose_skills_can_use_specific_folder(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            (source / "local").mkdir()
            with mock.patch("agent_skill_bridge.picker.checkbox") as checkbox:
                checkbox.return_value.ask.return_value = ["local"]
                self.assertEqual(choose_skills(source), ["local"])
            self.assertEqual(checkbox.call_args.kwargs["choices"], ["local"])

    def test_choose_harness_uses_space_then_enter(self) -> None:
        ctx = Context(Path.cwd(), {"default": {"project": ".agents", "global": "~/.agents"}, "tool": {}})
        with mock.patch("agent_skill_bridge.picker.select") as select:
            select.return_value.ask.return_value = "tool"
            self.assertEqual(choose_harness(ctx), "tool")
        select.assert_called_once()

    def test_choose_harness_can_exclude_default(self) -> None:
        ctx = Context(Path.cwd(), {"default": {"project": ".agents", "global": "~/.agents"}, "tool": {}})
        with mock.patch("agent_skill_bridge.picker.select") as select:
            select.return_value.ask.return_value = "tool"
            self.assertEqual(choose_harness(ctx, include_default=False), "tool")
        self.assertEqual(select.call_args.kwargs["choices"], ["tool"])


if __name__ == "__main__":
    unittest.main()
