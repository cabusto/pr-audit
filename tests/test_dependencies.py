from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from helpers import TempRepo
from pr_audit.analysis import analyze_repo


class DependencyTests(unittest.TestCase):
    def test_dependency_changes_across_pyproject_and_requirements(self) -> None:
        repo = TempRepo.create()
        repo.write_text(
            "pyproject.toml",
            """
[project]
dependencies = [
  "pydantic>=2.8",
]

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
""".strip()
            + "\n",
        )
        repo.write_text("requirements.txt", "jsonschema==4.0\n")
        repo.write_text("src/app.py", "def ok():\n    return 1\n")
        base = repo.commit("base")

        repo.write_text(
            "pyproject.toml",
            """
[project]
dependencies = [
  "pydantic>=2.9",
  "jsonschema",
]

[tool.poetry.group.dev.dependencies]
pytest = "^8.1"
""".strip()
            + "\n",
        )
        repo.write_text("requirements.txt", "jsonschema==4.0\nreferencing>=0.0\n")
        head = repo.commit("head")

        audit = analyze_repo(repo.root, base, head, generated_at="2024-01-01T00:00:00Z")
        changes = {(change.manifest, change.name, change.status): change for change in audit.dependencies}

        self.assertIn(("pyproject.toml", "pydantic", "changed"), changes)
        self.assertIn(("pyproject.toml", "jsonschema", "added"), changes)
        self.assertIn(("pyproject.toml", "pytest", "changed"), changes)
        self.assertIn(("requirements.txt", "referencing", "added"), changes)
        self.assertEqual(changes[("pyproject.toml", "pytest", "changed")].dependency_type, "development")
        self.assertEqual(changes[("pyproject.toml", "jsonschema", "added")].dependency_type, "runtime")
        self.assertFalse(audit.errors)
