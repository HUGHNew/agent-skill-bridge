from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent_skill_bridge.cli import main


class CliEntrypointTests(unittest.TestCase):
    def test_help_exits_successfully(self) -> None:
        output = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(output):
            main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("asb", output.getvalue())


if __name__ == "__main__":
    unittest.main()
