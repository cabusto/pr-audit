from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Metadata:
    base_ref: str
    head_ref: str
    generated_at: str


@dataclass(slots=True)
class CategoryCounts:
    production: int = 0
    tests: int = 0
    config: int = 0
    docs: int = 0
    dependency: int = 0
    other: int = 0


@dataclass(slots=True)
class Scope:
    loc_added: int = 0
    loc_deleted: int = 0
    files_changed: int = 0
    files_added: int = 0
    files_deleted: int = 0
    categories: CategoryCounts = field(default_factory=CategoryCounts)


@dataclass(slots=True)
class DependencyChange:
    name: str
    status: str
    before: str | None
    after: str | None
    dependency_type: str
    manifest: str
    section: str


@dataclass(slots=True)
class FunctionAudit:
    qualname: str
    lineno: int | None
    end_lineno: int | None
    loc_before: int | None
    loc_after: int | None
    cyclomatic_before: int | None
    cyclomatic_after: int | None
    nesting_before: int | None
    nesting_after: int | None


@dataclass(slots=True)
class FileStructureMetrics:
    classes_added: int = 0
    classes_removed: int = 0
    functions_added: int = 0
    functions_removed: int = 0


@dataclass(slots=True)
class StructureMetrics:
    production_files_added: int = 0
    production_files_modified: int = 0
    production_files_deleted: int = 0
    classes_added: int = 0
    classes_removed: int = 0
    functions_added: int = 0
    functions_removed: int = 0


@dataclass(slots=True)
class Hotspot:
    score: int
    severity: str
    reasons: list[dict[str, object]] = field(default_factory=list)


@dataclass(slots=True)
class FileAudit:
    path: str
    status: str
    category: str
    loc_added: int | None
    loc_deleted: int | None
    binary: bool = False
    renamed_from: str | None = None
    analysis_error: str | None = None
    functions: list[FunctionAudit] = field(default_factory=list)
    structure: FileStructureMetrics | None = None
    hotspot: Hotspot | None = None


@dataclass(slots=True)
class TestsMetrics:
    files_changed: int = 0
    files_added: int = 0
    loc_added: int = 0
    production_loc_added: int = 0
    production_test_ratio: float | None = None


@dataclass(slots=True)
class Summary:
    changed_functions_increased: int = 0
    hotspot_count: int = 0


@dataclass(slots=True)
class AnalyzerError:
    area: str
    path: str | None
    message: str


@dataclass(slots=True)
class Audit:
    metadata: Metadata
    scope: Scope
    dependencies: list[DependencyChange] = field(default_factory=list)
    tests: TestsMetrics = field(default_factory=TestsMetrics)
    structure: StructureMetrics = field(default_factory=StructureMetrics)
    files: list[FileAudit] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
    errors: list[AnalyzerError] = field(default_factory=list)
