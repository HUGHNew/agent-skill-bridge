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
from agent_skill_bridge.config import load_config_map


class ConfigCommandTests(unittest.TestCase):
    def test_config_add_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "custom", "-p", ".custom", "-g", str(Path(config_dir) / "custom")])
                    main(["config", "add", "empty"])

                map_path = Path(home) / ".agents" / "asb-mapper.json"
                self.assertIn('"custom"', map_path.read_text(encoding="utf-8"))
                self.assertIn('"empty": {}', map_path.read_text(encoding="utf-8"))

                with redirect_stdout(StringIO()):
                    main(["config", "remove", "empty"])
                self.assertNotIn('"empty"', map_path.read_text(encoding="utf-8"))

    def test_config_file_is_initialized_with_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                config = load_config_map()

                map_path = Path(home) / ".agents" / "asb-mapper.json"
                self.assertTrue(map_path.exists())
                self.assertIn("codex", config)
                self.assertIn('"default"', map_path.read_text(encoding="utf-8"))
                self.assertIn('"global": "~/.agents"', map_path.read_text(encoding="utf-8"))

    def test_config_list_output_format(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "custom", "-p", ".custom", "-g", "/tmp/custom"])

                output = StringIO()
                with redirect_stdout(output):
                    main(["config", "list"])

                expected = "".join(format_config_entry(harness, values) for harness, values in load_config_map().items())
                self.assertEqual(expected, output.getvalue())


def format_config_entry(harness: str, values: dict[str, str]) -> str:
    if not values:
        return f"{harness}: {{}}\n"
    fields = "\n\t".join(f"{key} = {value}" for key, value in values.items())
    return f"{harness}:\n\t{fields}\n"


if __name__ == "__main__":
    unittest.main()
