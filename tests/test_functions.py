from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from helpers import TempRepo
from pr_audit.analysis import analyze_repo


class FunctionTests(unittest.TestCase):
    def test_changed_python_functions_and_parse_failure_are_local(self) -> None:
        repo = TempRepo.create()
        repo.write_text(
            "src/routes.py",
            """
def outer(n):
    if n > 0:
        return n
    return 0


class Handler:
    def method(self, flag):
        if flag:
            return 1
        return 0


def untouched():
    return 5
""".strip()
            + "\n",
        )
        repo.write_text("src/broken.py", "def ok():\n    return 1\n")
        base = repo.commit("base")

        repo.write_text(
            "src/routes.py",
            """
def outer(n):
    if n > 0:
        if n > 10:
            return 10
        return n
    return 0


class Handler:
    def method(self, flag):
        if flag:
            for i in range(2):
                if i:
                    return 2
        return 0


def untouched():
    return 5
""".strip()
            + "\n",
        )
        repo.write_text("src/broken.py", "def broken(:\n")
        head = repo.commit("head")

        audit = analyze_repo(repo.root, base, head, generated_at="2024-01-01T00:00:00Z")
        routes = next(file_audit for file_audit in audit.files if file_audit.path == "src/routes.py")
        broken = next(file_audit for file_audit in audit.files if file_audit.path == "src/broken.py")

        self.assertEqual({function.qualname for function in routes.functions}, {"routes.Handler.method", "routes.outer"})
        outer = next(function for function in routes.functions if function.qualname == "routes.outer")
        method = next(function for function in routes.functions if function.qualname == "routes.Handler.method")
        self.assertEqual((outer.cyclomatic_before, outer.cyclomatic_after), (2, 3))
        self.assertEqual((outer.nesting_before, outer.nesting_after), (1, 2))
        self.assertEqual((method.cyclomatic_before, method.cyclomatic_after), (2, 4))
        self.assertEqual((method.nesting_before, method.nesting_after), (1, 3))
        self.assertIsNotNone(broken.analysis_error)
        self.assertFalse(broken.functions)
        self.assertTrue(any(error.path == "src/broken.py" for error in audit.errors))
        self.assertEqual(audit.summary.changed_functions_increased, 2)
