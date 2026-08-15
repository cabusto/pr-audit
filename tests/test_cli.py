from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import TempRepo


class CliTests(unittest.TestCase):
    def test_cli_writes_json_and_markdown(self) -> None:
        repo = TempRepo.create()
        repo.write_text("pyproject.toml", "[project]\ndependencies = [\"pydantic>=2.8\"]\n")
        repo.write_text("src/app.py", "def f():\n    return 1\n")
        base = repo.commit("base")
        repo.write_text("pyproject.toml", "[project]\ndependencies = [\"pydantic>=2.9\", \"jsonschema\"]\n")
        repo.write_text("src/app.py", "def f():\n    if True:\n        return 2\n    return 1\n")
        head = repo.commit("head")

        result = repo.run_cli("analyze", "--base", base, "--head", head)
        self.assertEqual(result.returncode, 0)
        self.assertIn("✓ audit.json", result.stdout)
        self.assertIn("✓ audit.md", result.stdout)

        data = json.loads((repo.root / "audit.json").read_text(encoding="utf-8"))
        self.assertEqual(data["metadata"]["base_ref"], base)
        self.assertEqual(data["metadata"]["head_ref"], head)
        self.assertEqual(data["scope"]["files_changed"], 2)
        self.assertIn("# PR Audit", (repo.root / "audit.md").read_text(encoding="utf-8"))

    def test_cli_handles_no_changes(self) -> None:
        repo = TempRepo.create()
        repo.write_text("src/app.py", "def f():\n    return 1\n")
        base = repo.commit("base")

        result = repo.run_cli("analyze", "--base", base, "--head", base)
        self.assertEqual(result.returncode, 0)
        data = json.loads((repo.root / "audit.json").read_text(encoding="utf-8"))
        self.assertEqual(data["scope"]["files_changed"], 0)
        self.assertEqual(data["dependencies"], [])

    def test_cli_rejects_invalid_ref(self) -> None:
        repo = TempRepo.create()
        repo.write_text("src/app.py", "def f():\n    return 1\n")
        base = repo.commit("base")

        result = repo.run_cli("analyze", "--base", "not-a-ref", "--head", base)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not-a-ref", result.stderr)

    def test_help_includes_example(self) -> None:
        repo = TempRepo.create()
        result = repo.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Examples:", result.stdout)
        self.assertIn("pr-audit analyze --base main --head HEAD", result.stdout)
