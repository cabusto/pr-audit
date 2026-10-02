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
        self.assertEqual(
            production.hotspot.reasons,
            [
                {"type": "loc_changed", "value": {"added": 10, "deleted": 0}},
                {"type": "largest_production_change"},
                {"type": "complexity_increase", "value": 4},
                {"type": "nesting_increase", "value": 2},
            ],
        )
        self.assertEqual(
            dependency.hotspot.reasons,
            [
                {"type": "loc_changed", "value": {"added": 1, "deleted": 0}},
                {"type": "runtime_dependency_added", "value": 1},
                {"type": "dependency_manifest"},
            ],
        )
        self.assertEqual(test_only.hotspot.reasons, [{"type": "loc_changed", "value": {"added": 5, "deleted": 0}}, {"type": "test_only"}])

    def test_deleted_production_file_is_down_weighted(self) -> None:
        deleted = FileAudit(
            path="src/legacy.py",
            status="deleted",
            category="production",
            loc_added=0,
            loc_deleted=40,
        )
        edited = FileAudit(
            path="src/app.py",
            status="modified",
            category="production",
            loc_added=12,
            loc_deleted=3,
        )

        score_hotspots([deleted, edited], [])

        self.assertEqual(deleted.hotspot.score, 10)
        self.assertEqual(edited.hotspot.score, 15)
        self.assertEqual(edited.hotspot.severity, "HIGH")
        self.assertEqual(
            deleted.hotspot.reasons,
            [{"type": "loc_changed", "value": {"added": 0, "deleted": 40}}, {"type": "production_file_deleted"}],
        )
        self.assertIn({"type": "largest_production_change"}, edited.hotspot.reasons)

    def test_ci_workflow_files_are_scored(self) -> None:
        workflow = FileAudit(
            path=".github/workflows/release.yml",
            status="modified",
            category="config",
            loc_added=2,
            loc_deleted=1,
        )
        action = FileAudit(
            path="action.yml",
            status="added",
            category="config",
            loc_added=80,
            loc_deleted=0,
        )
        removed_workflow = FileAudit(
            path=".github/workflows/old.yml",
            status="deleted",
            category="config",
            loc_added=0,
            loc_deleted=20,
        )
        other_config = FileAudit(
            path=".github/dependabot.yml",
            status="modified",
            category="config",
            loc_added=3,
            loc_deleted=0,
        )

        score_hotspots([workflow, action, removed_workflow, other_config], [])

        self.assertEqual(workflow.hotspot.score, 40)
        self.assertEqual(action.hotspot.score, 40)
        self.assertEqual(
            workflow.hotspot.reasons,
            [{"type": "loc_changed", "value": {"added": 2, "deleted": 1}}, {"type": "ci_workflow"}],
        )
        self.assertEqual(removed_workflow.hotspot.score, 0)
        self.assertIn({"type": "config_only"}, removed_workflow.hotspot.reasons)
        self.assertEqual(other_config.hotspot.score, 0)
