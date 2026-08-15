from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from ..git.diff import ChangedFile, DiffHunk
from ..models import FunctionAudit
from .complexity import analyze_function_metrics


@dataclass(slots=True)
class _CollectedFunction:
    qualname: str
    lineno: int
    end_lineno: int
    cyclomatic: int
    nesting: int


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, module_name: str | None = None) -> None:
        self.scope: list[str] = [module_name] if module_name else []
        self.functions: list[_CollectedFunction] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record(node)

    def _record(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        metrics = analyze_function_metrics(node)
        self.functions.append(
            _CollectedFunction(
                qualname=".".join([*self.scope, node.name]),
                lineno=node.lineno,
                end_lineno=node.end_lineno or node.lineno,
                cyclomatic=metrics.cyclomatic,
                nesting=metrics.nesting,
            )
        )
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()


def _parse_functions(source: str, *, filename: str) -> list[_CollectedFunction]:
    tree = ast.parse(source, filename=filename)
    collector = _FunctionCollector(module_name=Path(filename).stem)
    collector.visit(tree)
    return collector.functions


def _ranges_overlap(span_start: int, span_end: int, ranges: list[tuple[int, int]]) -> bool:
    for start, end in ranges:
        if start <= span_end and end >= span_start:
            return True
    return False


def _changed_ranges(chunks: list[DiffHunk]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    old_ranges: list[tuple[int, int]] = []
    new_ranges: list[tuple[int, int]] = []
    for chunk in chunks:
        if chunk.old_count > 0:
            old_ranges.append((chunk.old_start, chunk.old_start + chunk.old_count - 1))
        if chunk.new_count > 0:
            new_ranges.append((chunk.new_start, chunk.new_start + chunk.new_count - 1))
    return old_ranges, new_ranges


def analyze_changed_python_file(
    changed_file: ChangedFile,
    *,
    base_text: str | None,
    head_text: str | None,
    hunks: list[DiffHunk],
) -> list[FunctionAudit]:
    if not base_text and not head_text:
        return []

    try:
        base_functions = _parse_functions(base_text, filename=changed_file.old_path or changed_file.path) if base_text else []
        head_functions = _parse_functions(head_text, filename=changed_file.path) if head_text else []
    except SyntaxError as exc:
        raise SyntaxError(f"{changed_file.path}: {exc.msg}") from exc

    old_ranges, new_ranges = _changed_ranges(hunks)
    base_map = {function.qualname: function for function in base_functions}
    head_map = {function.qualname: function for function in head_functions}
    changed_names: set[str] = set()

    for function in base_functions:
        if _ranges_overlap(function.lineno, function.end_lineno, old_ranges):
            changed_names.add(function.qualname)
    for function in head_functions:
        if _ranges_overlap(function.lineno, function.end_lineno, new_ranges):
            changed_names.add(function.qualname)

    audits: list[FunctionAudit] = []
    for qualname in sorted(changed_names):
        base = base_map.get(qualname)
        head = head_map.get(qualname)
        audits.append(
            FunctionAudit(
                qualname=qualname,
                lineno=head.lineno if head else base.lineno if base else None,
                end_lineno=head.end_lineno if head else base.end_lineno if base else None,
                loc_before=(base.end_lineno - base.lineno + 1) if base else None,
                loc_after=(head.end_lineno - head.lineno + 1) if head else None,
                cyclomatic_before=base.cyclomatic if base else None,
                cyclomatic_after=head.cyclomatic if head else None,
                nesting_before=base.nesting if base else None,
                nesting_after=head.nesting if head else None,
            )
        )
    return audits
