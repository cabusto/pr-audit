from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pr_audit.models import DependencyChange, FileAudit, FunctionAudit
from pr_audit.scoring import score_hotspots


class HotspotTests(unittest.TestCase):
    def test_rankings_are_deterministic_and_explainable(self) -> None:
        production = FileAudit(
            path="src/app.py",
            status="modified",
            category="production",
            loc_added=10,
            loc_deleted=0,
            functions=[
                FunctionAudit(
                    qualname="app.run",
                    lineno=1,
                    end_lineno=10,
                    loc_before=10,
                    loc_after=14,
                    cyclomatic_before=2,
                    cyclomatic_after=6,
                    nesting_before=1,
                    nesting_after=3,
                )
            ],
        )
        dependency = FileAudit(
            path="pyproject.toml",
            status="modified",
            category="dependency",
            loc_added=1,
            loc_deleted=0,
        )
        small = FileAudit(
            path="src/small.py",
            status="modified",
            category="production",
            loc_added=1,
            loc_deleted=0,
        )
        test_only = FileAudit(
            path="tests/test_app.py",
            status="modified",
            category="tests",
            loc_added=5,
            loc_deleted=0,
        )
        dependencies = [
            DependencyChange(
                name="jsonschema",
                status="added",
                before=None,
                after=None,
                dependency_type="runtime",
                manifest="pyproject.toml",
                section="project.dependencies",
            )
        ]

        score_hotspots([production, dependency, small, test_only], dependencies)

        self.assertEqual(production.hotspot.severity, "HIGH")
        self.assertEqual(dependency.hotspot.severity, "MED")
        self.assertEqual(small.hotspot.severity, "LOW")
        self.assertEqual(test_only.hotspot.severity, "LOW")
        self.assertIn("complexity +4", production.hotspot.reasons)
        self.assertIn("max nesting +2", production.hotspot.reasons)
        self.assertIn("1 runtime dependencies added", dependency.hotspot.reasons)
        self.assertIn("test-only", test_only.hotspot.reasons)
