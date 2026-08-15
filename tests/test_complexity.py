from __future__ import annotations

import ast
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pr_audit.analyzers.complexity import analyze_function_metrics


class ComplexityTests(unittest.TestCase):
    def test_metrics_are_deterministic(self) -> None:
        source = """
def sample(x):
    if x and x > 0:
        for item in range(3):
            if item:
                pass
    elif x == 0:
        while False:
            pass
    return 1
"""
        module = ast.parse(source)
        function = module.body[0]
        metrics = analyze_function_metrics(function)
        self.assertEqual(metrics.cyclomatic, 7)
        self.assertEqual(metrics.nesting, 3)
