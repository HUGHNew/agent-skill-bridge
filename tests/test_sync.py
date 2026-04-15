from __future__ import annotations

import os
import sys
import tempfile
import unittest
import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent_skill_bridge.cli import main
from agent_skill_bridge.config import shared_store


class SyncCommandTests(unittest.TestCase):
    def test_sync_project_reuses_copy_logic_and_records_usage(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                src_root = Path(config_dir) / "src"
                dst_root = Path(config_dir) / "dst"
                with redirect_stdout(StringIO()):
                    main(["config", "add", "src", "-g", str(src_root)])
                    main(["config", "add", "dst", "-p", ".dst", "-g", str(dst_root)])
                (src_root / "skills" / "demo").mkdir(parents=True)
                (src_root / "skills" / "demo" / "SKILL.md").write_text("demo\n", encoding="utf-8")
                (shared_store() / "demo").mkdir(parents=True)
                (shared_store() / "demo" / "SKILL.md").write_text("demo\n", encoding="utf-8")

                with redirect_stdout(StringIO()):
                    main(["sync", "src", "dst", "--project", "--copy"])

                self.assertTrue((project_root / ".dst" / "skills" / "demo" / "SKILL.md").exists())
                usage = json.loads((Path(config_dir) / "agent-skill-bridge" / "usage.json").read_text(encoding="utf-8"))
                self.assertEqual(usage["dst"]["projects"][str(project_root.resolve())]["demo"], "copy")

    def test_sync_warns_for_source_only_skills_without_all(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                src_root = Path(config_dir) / "src"
                dst_root = Path(config_dir) / "dst"
                with redirect_stdout(StringIO()):
                    main(["config", "add", "src", "-g", str(src_root)])
                    main(["config", "add", "dst", "-p", ".dst", "-g", str(dst_root)])
                (src_root / "skills" / "source-only").mkdir(parents=True)
                (shared_store() / "shared").mkdir(parents=True)

                output = StringIO()
                error = StringIO()
                with redirect_stdout(output), redirect_stderr(error):
                    main(["sync", "src", "dst"])

                self.assertIn("warning: source skill not found in shared store: source-only", error.getvalue())
                self.assertTrue((Path(cwd) / ".dst" / "skills" / "shared").is_symlink())
                self.assertFalse((Path(cwd) / ".dst" / "skills" / "source-only").exists())

    def test_sync_all_adds_source_only_skills_to_shared_store(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                src_root = Path(config_dir) / "src"
                dst_root = Path(config_dir) / "dst"
                with redirect_stdout(StringIO()):
                    main(["config", "add", "src", "-g", str(src_root)])
                    main(["config", "add", "dst", "-p", ".dst", "-g", str(dst_root)])
                (src_root / "skills" / "source-only").mkdir(parents=True)

                output = StringIO()
                error = StringIO()
                with redirect_stdout(output), redirect_stderr(error):
                    main(["sync", "src", "dst", "-a"])

                self.assertIn("added to shared store: source-only", output.getvalue())
                self.assertEqual("", error.getvalue())
                self.assertTrue((shared_store() / "source-only").exists())
                self.assertTrue((Path(cwd) / ".dst" / "skills" / "source-only").is_symlink())

    def test_sync_empty_source_reports_done_without_syncing(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                src_root = Path(config_dir) / "src"
                dst_root = Path(config_dir) / "dst"
                with redirect_stdout(StringIO()):
                    main(["config", "add", "src", "-g", str(src_root)])
                    main(["config", "add", "dst", "-p", ".dst", "-g", str(dst_root)])
                (shared_store() / "shared").mkdir(parents=True)

                output = StringIO()
                with redirect_stdout(output):
                    main(["sync", "src", "dst"])

                self.assertIn("source has no skills:", output.getvalue())
                self.assertFalse((Path(cwd) / ".dst" / "skills" / "shared").exists())

    def test_sync_reports_synced_count(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                src_root = Path(config_dir) / "src"
                dst_root = Path(config_dir) / "dst"
                with redirect_stdout(StringIO()):
                    main(["config", "add", "src", "-g", str(src_root)])
                    main(["config", "add", "dst", "-p", ".dst", "-g", str(dst_root)])
                (src_root / "skills" / "shared").mkdir(parents=True)
                (shared_store() / "shared").mkdir(parents=True)

                output = StringIO()
                with redirect_stdout(output):
                    main(["sync", "src", "dst"])

                self.assertIn("synced 1 skills", output.getvalue())


if __name__ == "__main__":
    unittest.main()
