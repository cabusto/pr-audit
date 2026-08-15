from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(slots=True)
class FunctionMetrics:
    cyclomatic: int
    nesting: int


class _CyclomaticVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.count = 1

    def visit_If(self, node: ast.If) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.count += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.count += len(node.cases)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # pragma: no cover - nested defs skipped
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # pragma: no cover - nested defs skipped
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # pragma: no cover - nested defs skipped
        return


def _walk_block(statements: list[ast.stmt], depth: int) -> int:
    best = depth
    for statement in statements:
        best = max(best, _walk_statement(statement, depth))
    return best


def _walk_statement(statement: ast.stmt, depth: int) -> int:
    best = depth
    next_depth = depth + 1

    if isinstance(statement, ast.If):
        best = max(best, next_depth, _walk_block(statement.body, next_depth))
        if statement.orelse:
            if len(statement.orelse) == 1 and isinstance(statement.orelse[0], ast.If):
                best = max(best, _walk_statement(statement.orelse[0], depth))
            else:
                best = max(best, _walk_block(statement.orelse, next_depth))
        return best

    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
        best = max(best, next_depth, _walk_block(statement.body, next_depth))
        if getattr(statement, "orelse", None):
            best = max(best, _walk_block(statement.orelse, next_depth))
        return best

    if isinstance(statement, ast.Try):
        best = max(best, next_depth, _walk_block(statement.body, next_depth))
        for handler in statement.handlers:
            best = max(best, _walk_block(handler.body, next_depth))
        best = max(best, _walk_block(statement.orelse, next_depth))
        best = max(best, _walk_block(statement.finalbody, next_depth))
        return best

    if isinstance(statement, ast.Match):
        best = max(best, next_depth)
        for case in statement.cases:
            best = max(best, _walk_block(case.body, next_depth))
        return best

    return best


def analyze_function_metrics(node: ast.AST) -> FunctionMetrics:
    cyclomatic_visitor = _CyclomaticVisitor()
    body = getattr(node, "body", [])
    if isinstance(body, list):
        for statement in body:
            cyclomatic_visitor.visit(statement)
    body = getattr(node, "body", [])
    nesting = _walk_block(body, 0) if isinstance(body, list) else 0
    return FunctionMetrics(cyclomatic=cyclomatic_visitor.count, nesting=nesting)
