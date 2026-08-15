from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from helpers import TempRepo
from pr_audit.analysis import analyze_repo
from pr_audit.render import render_markdown


class DependencyTests(unittest.TestCase):
    def _audit(
        self,
        *,
        base_files: dict[str, str],
        head_files: dict[str, str],
        head_deletes: tuple[str, ...] = (),
    ):
        repo = TempRepo.create()
        for path, text in base_files.items():
            repo.write_text(path, text)
        base = repo.commit("base")
        for path in head_deletes:
            repo.remove(path)
        for path, text in head_files.items():
            repo.write_text(path, text)
        head = repo.commit("head")
        return analyze_repo(repo.root, base, head, generated_at="2024-01-01T00:00:00Z")

    def _changes(self, audit):
        return {(change.manifest, change.name, change.status): change for change in audit.dependencies}

    def test_dependency_added_detected(self) -> None:
        audit = self._audit(
            base_files={"pyproject.toml": "[project]\ndependencies = [\"pydantic>=2.8\"]\n"},
            head_files={"pyproject.toml": "[project]\ndependencies = [\"pydantic>=2.8\", \"jsonschema\"]\n"},
        )

        changes = self._changes(audit)
        self.assertIn(("pyproject.toml", "jsonschema", "added"), changes)
        self.assertEqual(changes[("pyproject.toml", "jsonschema", "added")].dependency_type, "runtime")
        self.assertFalse(audit.errors)

    def test_dependency_removed_detected(self) -> None:
        audit = self._audit(
            base_files={"pyproject.toml": "[project]\ndependencies = [\"pydantic>=2.8\", \"jsonschema\"]\n"},
            head_files={"pyproject.toml": "[project]\ndependencies = [\"pydantic>=2.8\"]\n"},
        )

        changes = self._changes(audit)
        self.assertIn(("pyproject.toml", "jsonschema", "removed"), changes)
        self.assertEqual(changes[("pyproject.toml", "jsonschema", "removed")].dependency_type, "runtime")
        self.assertFalse(audit.errors)

    def test_dependency_version_changed_detected(self) -> None:
        audit = self._audit(
            base_files={"pyproject.toml": "[project]\ndependencies = [\"pydantic>=2.8\"]\n"},
            head_files={"pyproject.toml": "[project]\ndependencies = [\"pydantic>=2.9\"]\n"},
        )

        changes = self._changes(audit)
        change = changes[("pyproject.toml", "pydantic", "changed")]
        self.assertEqual((change.before, change.after), (">=2.8", ">=2.9"))
        self.assertEqual(change.dependency_type, "runtime")
        self.assertFalse(audit.errors)

    def test_dev_dependency_added_detected(self) -> None:
        audit = self._audit(
            base_files={"requirements-dev.txt": "pytest>=8.0\n"},
            head_files={"requirements-dev.txt": "pytest>=8.0\nmypy>=1.0\n"},
        )

        changes = self._changes(audit)
        change = changes[("requirements-dev.txt", "mypy", "added")]
        self.assertEqual(change.dependency_type, "development")
        self.assertFalse(audit.errors)

    def test_unchanged_manifest_reports_no_dependency_changes_detected(self) -> None:
        audit = self._audit(
            base_files={
                "pyproject.toml": "[project]\ndependencies = [\"pydantic>=2.8\"]\n",
                "src/app.py": "def ok():\n    return 1\n",
            },
            head_files={"src/app.py": "def ok():\n    return 2\n"},
        )

        self.assertFalse(audit.dependencies)
        self.assertEqual(audit.scope.categories.dependency, 0)
        self.assertIn("No dependency manifest changes detected", render_markdown(audit))

    def test_new_dependency_manifest_detected(self) -> None:
        audit = self._audit(
            base_files={"src/app.py": "def ok():\n    return 1\n"},
            head_files={
                "requirements.txt": "jsonschema>=4.0\n",
                "src/app.py": "def ok():\n    return 2\n",
            },
        )

        changes = self._changes(audit)
        change = changes[("requirements.txt", "jsonschema", "added")]
        self.assertEqual(change.dependency_type, "runtime")
        self.assertEqual(audit.scope.categories.dependency, 1)
        self.assertFalse(audit.errors)

    def test_deleted_dependency_manifest_detected(self) -> None:
        audit = self._audit(
            base_files={
                "requirements.txt": "jsonschema>=4.0\n",
                "src/app.py": "def ok():\n    return 1\n",
            },
            head_files={"src/app.py": "def ok():\n    return 2\n"},
            head_deletes=("requirements.txt",),
        )

        changes = self._changes(audit)
        change = changes[("requirements.txt", "jsonschema", "removed")]
        self.assertEqual(change.dependency_type, "runtime")
        self.assertEqual(audit.scope.categories.dependency, 1)
        self.assertFalse(audit.errors)

    def test_dependency_lock_file_reports_unsupported_manifest(self) -> None:
        audit = self._audit(
            base_files={
                "poetry.lock": "jsonschema 4.0\n",
                "src/app.py": "def ok():\n    return 1\n",
            },
            head_files={
                "poetry.lock": "jsonschema 4.1\n",
                "src/app.py": "def ok():\n    return 2\n",
            },
        )

        self.assertFalse(audit.dependencies)
        self.assertEqual(audit.scope.categories.dependency, 1)
        self.assertTrue(any(error.area == "dependencies" and error.path == "poetry.lock" for error in audit.errors))
        markdown = render_markdown(audit)
        self.assertIn("Dependency manifest changes detected, but no dependency-level changes could be parsed", markdown)
        self.assertIn("poetry.lock", markdown)
