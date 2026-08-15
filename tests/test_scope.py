from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pr_audit.analyzers import classify_path
from pr_audit.git.diff import ChangedFile
from pr_audit.analyzers import summarize_scope, summarize_tests


class ScopeTests(unittest.TestCase):
    def test_classification_order(self) -> None:
        cases = {
            "pyproject.toml": "dependency",
            "requirements.txt": "dependency",
            "tests/test_app.py": "tests",
            "src/test_utils.py": "tests",
            "docs/readme.md": "docs",
            ".github/workflows/ci.yml": "config",
            "src/app.py": "production",
            "assets/logo.png": "other",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(classify_path(path), expected)

    def test_scope_and_tests_metrics(self) -> None:
        files = [
            ChangedFile(path="src/app.py", old_path=None, status="modified", loc_added=10, loc_deleted=2, binary=False),
            ChangedFile(path="tests/test_app.py", old_path=None, status="added", loc_added=7, loc_deleted=0, binary=False),
            ChangedFile(path="docs/readme.md", old_path=None, status="modified", loc_added=3, loc_deleted=1, binary=False),
        ]
        scope = summarize_scope(files)
        tests = summarize_tests(files)
        self.assertEqual(scope.files_changed, 3)
        self.assertEqual(scope.files_added, 1)
        self.assertEqual(scope.files_deleted, 0)
        self.assertEqual(scope.categories.production, 1)
        self.assertEqual(scope.categories.tests, 1)
        self.assertEqual(scope.categories.docs, 1)
        self.assertEqual(tests.files_changed, 1)
        self.assertEqual(tests.files_added, 1)
        self.assertEqual(tests.loc_added, 7)
        self.assertEqual(tests.production_loc_added, 10)
        self.assertEqual(tests.production_test_ratio, 10 / 7)
