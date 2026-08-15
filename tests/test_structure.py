from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from helpers import TempRepo
from pr_audit.analysis import analyze_repo


class StructureTests(unittest.TestCase):
    def test_structure_counts_ignore_test_files_and_nested_functions(self) -> None:
        repo = TempRepo.create()
        repo.write_text(
            "src/core.py",
            """
def changed():
    return 1
""".strip()
            + "\n",
        )
        repo.write_text(
            "src/deleted.py",
            """
class Removed:
    def method(self):
        return 1


def old_function():
    return 2
""".strip()
            + "\n",
        )
        repo.write_text(
            "tests/test_helpers.py",
            """
def test_helper():
    return 1
""".strip()
            + "\n",
        )
        base = repo.commit("base")

        repo.write_text(
            "src/core.py",
            """
def changed():
    def helper():
        return 2

    return helper()
""".strip()
            + "\n",
        )
        repo.write_text(
            "src/new_module.py",
            """
def top_level():
    return 3


class Added:
    def method(self):
        return 4

    async def async_method(self):
        return 5
""".strip()
            + "\n",
        )
        repo.remove("src/deleted.py")
        repo.write_text(
            "tests/test_helpers.py",
            """
def test_helper():
    return 2


def test_extra():
    return 3
""".strip()
            + "\n",
        )
        head = repo.commit("head")

        audit = analyze_repo(repo.root, base, head, generated_at="2024-01-01T00:00:00Z")

        self.assertEqual(
            (
                audit.structure.production_files_added,
                audit.structure.production_files_modified,
                audit.structure.production_files_deleted,
            ),
            (1, 1, 1),
        )
        self.assertEqual(
            (
                audit.structure.classes_added,
                audit.structure.classes_removed,
                audit.structure.functions_added,
                audit.structure.functions_removed,
            ),
            (1, 1, 3, 2),
        )

        core = next(file_audit for file_audit in audit.files if file_audit.path == "src/core.py")
        new_module = next(file_audit for file_audit in audit.files if file_audit.path == "src/new_module.py")
        deleted = next(file_audit for file_audit in audit.files if file_audit.path == "src/deleted.py")
        tests = next(file_audit for file_audit in audit.files if file_audit.path == "tests/test_helpers.py")

        self.assertIsNotNone(core.structure)
        self.assertEqual((core.structure.classes_added, core.structure.functions_added), (0, 0))
        self.assertEqual((new_module.structure.classes_added, new_module.structure.functions_added), (1, 3))
        self.assertEqual((deleted.structure.classes_removed, deleted.structure.functions_removed), (1, 2))
        self.assertIsNone(tests.structure)
