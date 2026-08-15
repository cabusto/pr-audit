from __future__ import annotations

import json
import sys
from pathlib import Path
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pr_audit.models import (
    AnalyzerError,
    Audit,
    CategoryCounts,
    DependencyChange,
    FileAudit,
    FileStructureMetrics,
    FunctionAudit,
    Hotspot,
    Metadata,
    Scope,
    StructureMetrics,
    Summary,
    TestsMetrics,
)
from pr_audit.render import render_json, render_markdown


class RendererTests(unittest.TestCase):
    def _audit(self) -> Audit:
        return Audit(
            metadata=Metadata(base_ref="main", head_ref="HEAD", generated_at="2024-01-01T00:00:00Z"),
            scope=Scope(
                loc_added=12,
                loc_deleted=4,
                files_changed=2,
                files_added=1,
                files_deleted=0,
                categories=CategoryCounts(production=1, tests=1, config=0, docs=0, dependency=0, other=0),
            ),
            dependencies=[
                DependencyChange(
                    name="jsonschema",
                    status="added",
                    before=None,
                    after=None,
                    dependency_type="runtime",
                    manifest="pyproject.toml",
                    section="project.dependencies",
                ),
                DependencyChange(
                    name="pydantic",
                    status="changed",
                    before="2.8",
                    after="2.9",
                    dependency_type="runtime",
                    manifest="pyproject.toml",
                    section="project.dependencies",
                ),
            ],
            tests=TestsMetrics(files_changed=1, files_added=1, loc_added=7, production_loc_added=5, production_test_ratio=5 / 7),
            structure=StructureMetrics(
                production_files_added=0,
                production_files_modified=1,
                production_files_deleted=0,
                classes_added=1,
                classes_removed=0,
                functions_added=1,
                functions_removed=0,
            ),
            files=[
                FileAudit(
                    path="src/app.py",
                    status="modified",
                    category="production",
                    loc_added=10,
                    loc_deleted=2,
                    functions=[
                        FunctionAudit(
                            qualname="app.run",
                            lineno=10,
                            end_lineno=30,
                            loc_before=21,
                            loc_after=26,
                            cyclomatic_before=4,
                            cyclomatic_after=7,
                            nesting_before=1,
                            nesting_after=3,
                        )
                    ],
                    structure=FileStructureMetrics(classes_added=1, classes_removed=0, functions_added=1, functions_removed=0),
                    hotspot=Hotspot(
                        score=112,
                        severity="HIGH",
                        reasons=[
                            {"type": "loc_changed", "value": {"added": 10, "deleted": 2}},
                            {"type": "complexity_increase", "value": 3},
                            {"type": "nesting_increase", "value": 2},
                        ],
                    ),
                ),
                FileAudit(
                    path="tests/test_app.py",
                    status="added",
                    category="tests",
                    loc_added=7,
                    loc_deleted=0,
                    structure=None,
                    hotspot=Hotspot(
                        score=0,
                        severity="LOW",
                        reasons=[
                            {"type": "loc_changed", "value": {"added": 7, "deleted": 0}},
                            {"type": "test_only"},
                        ],
                    ),
                ),
            ],
            summary=Summary(changed_functions_increased=1, hotspot_count=1),
            errors=[AnalyzerError(area="dependencies", path="pyproject.toml", message="")]
        )

    def test_json_snapshot(self) -> None:
        audit = self._audit()
        data = json.loads(render_json(audit))
        self.assertEqual(
            data,
            {
                "metadata": {
                    "base_ref": "main",
                    "head_ref": "HEAD",
                    "generated_at": "2024-01-01T00:00:00Z",
                },
                "scope": {
                    "loc_added": 12,
                    "loc_deleted": 4,
                    "files_changed": 2,
                    "files_added": 1,
                    "files_deleted": 0,
                    "categories": {
                        "production": 1,
                        "tests": 1,
                        "config": 0,
                        "docs": 0,
                        "dependency": 0,
                        "other": 0,
                    },
                },
                "dependencies": [
                    {
                        "name": "jsonschema",
                        "status": "added",
                        "before": None,
                        "after": None,
                        "dependency_type": "runtime",
                        "manifest": "pyproject.toml",
                        "section": "project.dependencies",
                    },
                    {
                        "name": "pydantic",
                        "status": "changed",
                        "before": "2.8",
                        "after": "2.9",
                        "dependency_type": "runtime",
                        "manifest": "pyproject.toml",
                        "section": "project.dependencies",
                    },
                ],
                "tests": {
                    "files_changed": 1,
                    "files_added": 1,
                    "loc_added": 7,
                    "production_loc_added": 5,
                    "production_test_ratio": 5 / 7,
                },
                "structure": {
                    "production_files_added": 0,
                    "production_files_modified": 1,
                    "production_files_deleted": 0,
                    "classes_added": 1,
                    "classes_removed": 0,
                    "functions_added": 1,
                    "functions_removed": 0,
                },
                "files": [
                    {
                        "path": "src/app.py",
                        "status": "modified",
                        "category": "production",
                        "loc_added": 10,
                        "loc_deleted": 2,
                        "binary": False,
                        "renamed_from": None,
                        "analysis_error": None,
                        "functions": [
                            {
                                "qualname": "app.run",
                                "lineno": 10,
                                "end_lineno": 30,
                                "loc_before": 21,
                                "loc_after": 26,
                                "cyclomatic_before": 4,
                                "cyclomatic_after": 7,
                                "nesting_before": 1,
                                "nesting_after": 3,
                            }
                        ],
                        "structure": {
                            "classes_added": 1,
                            "classes_removed": 0,
                            "functions_added": 1,
                            "functions_removed": 0,
                        },
                        "hotspot": {
                            "score": 112,
                            "severity": "HIGH",
                            "reasons": [
                                {"type": "loc_changed", "value": {"added": 10, "deleted": 2}},
                                {"type": "complexity_increase", "value": 3},
                                {"type": "nesting_increase", "value": 2},
                            ],
                        },
                    },
                    {
                        "path": "tests/test_app.py",
                        "status": "added",
                        "category": "tests",
                        "loc_added": 7,
                        "loc_deleted": 0,
                        "binary": False,
                        "renamed_from": None,
                        "analysis_error": None,
                        "functions": [],
                        "structure": None,
                        "hotspot": {
                            "score": 0,
                            "severity": "LOW",
                            "reasons": [
                                {"type": "loc_changed", "value": {"added": 7, "deleted": 0}},
                                {"type": "test_only"},
                            ],
                        },
                    },
                ],
                "summary": {
                    "changed_functions_increased": 1,
                    "hotspot_count": 1,
                },
                "errors": [
                    {
                        "area": "dependencies",
                        "path": "pyproject.toml",
                        "message": "",
                    }
                ],
            },
        )

    def test_markdown_snapshot(self) -> None:
        audit = self._audit()
        markdown = render_markdown(audit)
        self.assertEqual(
            markdown,
            textwrap.dedent(
                """\
                # PR Audit

                ## Scope
                +12 / -4 LOC
                2 files changed · 1 added · 0 deleted

                Production  1
                Tests       1
                Config      0
                Docs        0
                Dependency  0
                Other       0

                ## Dependencies
                Added
                + jsonschema

                Updated
                pydantic 2.8 -> 2.9

                ## Tests
                1 test files changed · 1 added
                7 test LOC added
                5 production LOC added
                Production:test LOC ratio 0.7:1

                ## Structure
                Production files
                0 added · 1 modified · 0 deleted

                Python structure
                1 class added
                1 function/method added

                ## Complexity
                1 changed functions increased in complexity

                src/app.py: run
                LOC         21 -> 26
                Complexity   4 -> 7
                Nesting      1 -> 3

                ## Review hotspots
                HIGH  src/app.py
                      +10 / -2 LOC
                      Complexity +3
                      Max nesting +2

                LOW   tests/test_app.py
                      +7 LOC
                      test-only
                """
            ),
        )
