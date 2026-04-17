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
from agent_skill_bridge.usage import record_global_usage, record_usage


class UsageCommandTests(unittest.TestCase):
    def test_usage_prints_globals_then_projects(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                record_global_usage("default", "codex", "shared-a", "link")
                record_global_usage("default", "codex", "shared-b", "copy")
                record_global_usage("claude-code", "codex", "claude-only", "link")
                record_usage("codex", project, "project-skill", "copy")

                output = StringIO()
                with redirect_stdout(output):
                    main(["usage"])

                self.assertEqual(
                    "\n".join([
                        "[global]:",
                        "codex",
                        "  - shared-a",
                        "  - shared-b",
                        "",
                        "[project]:",
                        "codex",
                        f"  {project.resolve()}",
                        "    - project-skill",
                        "",
                    ]),
                    output.getvalue(),
                )


if __name__ == "__main__":
    unittest.main()
