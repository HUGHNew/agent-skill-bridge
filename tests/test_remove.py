from __future__ import annotations

import json
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
from agent_skill_bridge.skills import copy_skill, link_skill
from agent_skill_bridge.usage import record_usage


class RemoveCommandTests(unittest.TestCase):
    def test_config_remove_all_deletes_related_skill_paths(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                global_root = Path(config_dir) / "tool"
                project_root = Path(cwd)
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(global_root)])

                (global_root / "skills" / "demo").mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {
                        "project": ".agents",
                        "global": str(Path(home) / ".agents"),
                    },
                    "tool": {
                        "project": ".tool",
                        "global": str(global_root),
                    },
                })
                (shared_store() / "demo").mkdir(parents=True)
                copy_skill("demo", "tool", project=True, ctx=ctx)

                with mock.patch("pathlib.Path.cwd", return_value=project_root):
                    with redirect_stdout(StringIO()):
                        main(["config", "remove", "tool", "-a"])

                self.assertFalse((global_root / "skills").exists())
                self.assertFalse((project_root / ".tool" / "skills").exists())

    def test_remove_project_folder_removes_project_skill(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                (shared_store() / "demo").mkdir(parents=True)
                with redirect_stdout(StringIO()):
                    main(["copy", "default", "demo"])
                folder = Path(cwd) / ".agents" / "skills" / "demo"

                with redirect_stdout(StringIO()):
                    main(["remove", "default", str(folder)])

                self.assertFalse(folder.exists())

    def test_remove_project_folder_ignores_global_flag(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(Path(config_dir) / "tool")])
                (shared_store() / "demo").mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {"project": ".agents", "global": str(Path(home) / ".agents")},
                    "tool": {"project": ".tool", "global": str(Path(config_dir) / "tool")},
                })
                copy_skill("demo", "tool", project=True, ctx=ctx)
                copy_skill("demo", "tool", project=False, ctx=ctx)
                folder = project_root / ".tool" / "skills" / "demo"
                global_folder = Path(config_dir) / "tool" / "skills" / "demo"

                with redirect_stdout(StringIO()):
                    main(["remove", "tool", str(folder), "--global"])

                self.assertFalse(folder.exists())
                self.assertTrue(global_folder.exists())

    def test_remove_link_outputs_link_and_shared_store_removals(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                (shared_store() / "demo").mkdir(parents=True)
                link_skill("demo", "default", project=True, ctx=Context(project_root, {
                    "default": {"project": ".agents", "global": str(Path(home) / ".agents")},
                }))

                output = StringIO()
                with redirect_stdout(output):
                    main(["remove", "default", "demo", "--link"])

                self.assertFalse((project_root / ".agents" / "skills" / "demo").exists())
                self.assertFalse((shared_store() / "demo").exists())
                self.assertIn("\033[31m[remove]\033[0m[project] \033[3mdemo\033[0m", output.getvalue())
                self.assertIn("\033[31m[remove]\033[0m\033[1m[global]\033[0m \033[3mdemo\033[0m", output.getvalue())

    def test_remove_project_skill_cleans_empty_project_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                (shared_store() / "demo").mkdir(parents=True)
                with redirect_stdout(StringIO()):
                    main(["copy", "default", "demo"])

                with redirect_stdout(StringIO()):
                    main(["remove", "default", "demo"])

                self.assertFalse((project_root / ".agents").exists())

    def test_remove_project_skill_keeps_prefix_with_other_content(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                (shared_store() / "demo").mkdir(parents=True)
                with redirect_stdout(StringIO()):
                    main(["copy", "default", "demo"])
                (project_root / ".agents" / "config.json").write_text("{}\n", encoding="utf-8")

                with redirect_stdout(StringIO()):
                    main(["remove", "default", "demo"])

                self.assertTrue((project_root / ".agents").exists())
                self.assertTrue((project_root / ".agents" / "skills").exists())

    def test_remove_global_folder_uses_all_logic(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                default_global = Path(home) / ".agents" / "skills" / "demo"
                default_global.mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {"project": ".agents", "global": str(Path(home) / ".agents")},
                })
                copy_skill("demo", "default", project=True, ctx=ctx)

                with mock.patch("agent_skill_bridge.skills.subprocess.run") as run:
                    with redirect_stdout(StringIO()):
                        main(["remove", "default", str(default_global)])

                self.assertFalse(default_global.exists())
                self.assertFalse((project_root / ".agents" / "skills" / "demo").exists())
                run.assert_called_once_with(["npx", "skills", "remove", "demo", "-g", "-a", "universal", "-y"], check=True)

    def test_remove_all_keeps_usage_for_missing_recorded_project_path(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            missing_project = Path(cwd) / "missing"
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                (Path(home) / ".agents" / "skills" / "demo").mkdir(parents=True)
                record_usage("default", missing_project, "demo", "copy")

                with mock.patch("agent_skill_bridge.skills.subprocess.run") as run:
                    with redirect_stdout(StringIO()):
                        main(["remove", "default", "demo", "--all"])

                usage_path = Path(home) / ".agents" / "asb-usage.json"
                usage = json.loads(usage_path.read_text(encoding="utf-8"))
                self.assertEqual(usage["default"]["projects"][str(missing_project.resolve())]["demo"], "copy")
                run.assert_called_once_with(["npx", "skills", "remove", "demo", "-g", "-a", "universal", "-y"], check=True)

    def test_remove_all_deletes_default_global_and_usage_locations(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(Path(config_dir) / "tool")])
                default_global = Path(home) / ".agents" / "skills" / "demo"
                default_global.mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {"project": ".agents", "global": str(Path(home) / ".agents")},
                    "tool": {"project": ".tool", "global": str(Path(config_dir) / "tool")},
                })
                copy_skill("demo", "tool", project=True, ctx=ctx)

                output = StringIO()
                with mock.patch("agent_skill_bridge.skills.subprocess.run") as run:
                    with redirect_stdout(output):
                        main(["remove", "default", "demo", "--all"])

                self.assertFalse(default_global.exists())
                self.assertFalse((project_root / ".tool" / "skills" / "demo").exists())
                self.assertIn("\033[31m[remove]\033[0m[project] \033[3mdemo\033[0m", output.getvalue())
                run.assert_called_once_with(["npx", "skills", "remove", "demo", "-g", "-a", "universal", "-y"], check=True)

    def test_remove_all_falls_back_when_npx_fails(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                default_global = Path(home) / ".agents" / "skills" / "demo"
                default_global.mkdir(parents=True)

                with mock.patch("agent_skill_bridge.skills.subprocess.run", side_effect=FileNotFoundError("npx")):
                    with redirect_stdout(StringIO()), mock.patch("sys.stderr", StringIO()) as error:
                        main(["remove", "default", "demo", "--all"])

                self.assertFalse(default_global.exists())
                self.assertIn("warning: failed to remove default global skill with npx", error.getvalue())

    def test_remove_all_cleans_empty_recorded_project_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(Path(config_dir) / "tool")])
                (shared_store() / "demo").mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {"project": ".agents", "global": str(Path(home) / ".agents")},
                    "tool": {"project": ".tool", "global": str(Path(config_dir) / "tool")},
                })
                copy_skill("demo", "tool", project=True, ctx=ctx)

                with mock.patch("agent_skill_bridge.skills.subprocess.run"):
                    with redirect_stdout(StringIO()):
                        main(["remove", "default", "demo", "--all"])

                self.assertFalse((project_root / ".tool").exists())

    def test_remove_project_usage_keeps_global_usage_for_same_harness(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(Path(config_dir) / "tool")])
                (shared_store() / "project-skill").mkdir(parents=True)
                (shared_store() / "global-skill").mkdir(parents=True)
                ctx = Context(project_root, {
                    "default": {"project": ".agents", "global": str(Path(home) / ".agents")},
                    "tool": {"project": ".tool", "global": str(Path(config_dir) / "tool")},
                })
                copy_skill("project-skill", "tool", project=True, ctx=ctx)
                link_skill("global-skill", "tool", project=False, ctx=ctx)

                with redirect_stdout(StringIO()):
                    main(["remove", "tool", "project-skill"])

                usage = json.loads((Path(home) / ".agents" / "asb-usage.json").read_text(encoding="utf-8"))
                self.assertEqual(usage["default"]["globals"]["tool"]["global-skill"], "link")

    def test_remove_without_skill_picks_from_project_level(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            project_root = Path(cwd)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}), mock.patch("pathlib.Path.cwd", return_value=project_root):
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(Path(config_dir) / "tool")])
                folder = project_root / ".tool" / "skills"
                (folder / "project-skill").mkdir(parents=True)
                (Path(home) / ".agents" / "skills" / "shared-only").mkdir(parents=True)

                with (
                    mock.patch("agent_skill_bridge.commands.choose_skills", return_value=["project-skill"]) as skill_picker,
                    redirect_stdout(StringIO()),
                ):
                    main(["remove", "tool"])

                self.assertEqual(skill_picker.call_args.args, (folder,))
                self.assertFalse((folder / "project-skill").exists())

    def test_remove_without_skill_picks_from_global_level(self) -> None:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_dir, "HOME": home}):
                global_root = Path(config_dir) / "tool"
                with redirect_stdout(StringIO()):
                    main(["config", "add", "tool", "-p", ".tool", "-g", str(global_root)])
                folder = global_root / "skills"
                (folder / "global-skill").mkdir(parents=True)

                with (
                    mock.patch("agent_skill_bridge.commands.choose_skills", return_value=["global-skill"]) as skill_picker,
                    redirect_stdout(StringIO()),
                ):
                    main(["remove", "tool", "--global"])

                self.assertEqual(skill_picker.call_args.args, (folder,))
                self.assertFalse((folder / "global-skill").exists())


if __name__ == "__main__":
    unittest.main()
