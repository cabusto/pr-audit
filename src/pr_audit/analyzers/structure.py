from __future__ import annotations

import ast
from pathlib import Path

from ..git.diff import ChangedFile
from ..models import FileStructureMetrics


class _StructureCollector(ast.NodeVisitor):
    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self.class_scope: list[str] = []
        self.class_names: set[str] = set()
        self.function_names: set[str] = set()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Only count definitions at module/class scope. Definitions inside
        # functions are implementation details, not structural changes.
        self.class_names.add(".".join([self.module_name, *self.class_scope, node.name]))
        self.class_scope.append(node.name)
        for child in node.body:
            self.visit(child)
        self.class_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_names.add(".".join([self.module_name, *self.class_scope, node.name]))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_names.add(".".join([self.module_name, *self.class_scope, node.name]))


def _collect_names(source: str, *, filename: str) -> tuple[set[str], set[str]]:
    tree = ast.parse(source, filename=filename)
    collector = _StructureCollector(module_name=Path(filename).stem)
    collector.visit(tree)
    return collector.class_names, collector.function_names


def analyze_python_structure(
    changed_file: ChangedFile,
    *,
    base_text: str | None,
    head_text: str | None,
) -> FileStructureMetrics:
    module_path = changed_file.path if changed_file.status != "deleted" else changed_file.old_path or changed_file.path

    try:
        base_classes, base_functions = _collect_names(base_text, filename=module_path) if base_text else (set(), set())
        head_classes, head_functions = _collect_names(head_text, filename=module_path) if head_text else (set(), set())
    except SyntaxError as exc:
        raise SyntaxError(f"{changed_file.path}: {exc.msg}") from exc

    return FileStructureMetrics(
        classes_added=len(head_classes - base_classes),
        classes_removed=len(base_classes - head_classes),
        functions_added=len(head_functions - base_functions),
        functions_removed=len(base_functions - head_functions),
    )
