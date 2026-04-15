from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent_skill_bridge.config import shared_store
from agent_skill_bridge.picker import choose_skills


class PickerTests(unittest.TestCase):
    def test_choose_skills_uses_tui_picker(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}):
                (shared_store() / "demo").mkdir(parents=True)
                with mock.patch("agent_skill_bridge.picker.curses.wrapper", return_value=["demo"]) as wrapper:
                    self.assertEqual(choose_skills(), ["demo"])
                wrapper.assert_called_once()


if __name__ == "__main__":
    unittest.main()
