from __future__ import annotations

from pathlib import Path

from ..models import Audit, DependencyChange, FileAudit, FunctionAudit


def _fmt_int(value: int) -> str:
    return f"{value:,}"


def _fmt_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}:1"


def _render_scope(audit: Audit) -> list[str]:
    scope = audit.scope
    lines = [
        "## Scope",
        f"+{_fmt_int(scope.loc_added)} / -{_fmt_int(scope.loc_deleted)} LOC",
        f"{_fmt_int(scope.files_changed)} files changed · {_fmt_int(scope.files_added)} added · {_fmt_int(scope.files_deleted)} deleted",
        "",
        f"Production  {_fmt_int(scope.categories.production)}",
        f"Tests       {_fmt_int(scope.categories.tests)}",
        f"Config      {_fmt_int(scope.categories.config)}",
        f"Docs        {_fmt_int(scope.categories.docs)}",
        f"Dependency  {_fmt_int(scope.categories.dependency)}",
        f"Other       {_fmt_int(scope.categories.other)}",
    ]
    return lines


def _group_dependency_changes(changes: list[DependencyChange]) -> list[str]:
    added = sorted((change for change in changes if change.status == "added"), key=lambda change: change.name)
    removed = sorted((change for change in changes if change.status == "removed"), key=lambda change: change.name)
    changed = sorted((change for change in changes if change.status == "changed"), key=lambda change: change.name)
    lines = ["## Dependencies"]
    if not changes:
        lines.append("No changes")
        return lines
    if added:
        lines.append("Added")
        for change in added:
            lines.append(f"+ {change.name}")
    if removed:
        lines.append("")
        lines.append("Removed")
        for change in removed:
            lines.append(f"- {change.name}")
    if changed:
        lines.append("")
        lines.append("Updated")
        for change in changed:
            before = change.before or "?"
            after = change.after or "?"
            lines.append(f"{change.name} {before} -> {after}")
    return lines


def _render_tests(audit: Audit) -> list[str]:
    tests = audit.tests
    return [
        "## Tests",
        f"{_fmt_int(tests.files_changed)} test files changed · {_fmt_int(tests.files_added)} added",
        f"{_fmt_int(tests.loc_added)} test LOC added",
        f"{_fmt_int(tests.production_loc_added)} production LOC added",
        f"Production:test LOC ratio {_fmt_ratio(tests.production_test_ratio)}",
    ]


def _render_complexity(audit: Audit) -> list[str]:
    changed = [
        (file_audit, function)
        for file_audit in audit.files
        for function in file_audit.functions
        if function.cyclomatic_before is not None
        and function.cyclomatic_after is not None
        and function.cyclomatic_after > function.cyclomatic_before
    ]
    changed.sort(
        key=lambda item: (
            -(item[1].cyclomatic_after - item[1].cyclomatic_before),
            -(item[1].nesting_after - item[1].nesting_before),
            item[1].qualname,
        )
    )
    lines = ["## Complexity", f"{_fmt_int(len(changed))} changed functions increased in complexity"]
    if not changed:
        return lines
    lines.append("")
    for file_audit, function in changed[:5]:
        lines.append(_format_function_label(file_audit, function))
        lines.append(f"LOC         {function.loc_before} -> {function.loc_after}")
        lines.append(f"Complexity   {function.cyclomatic_before} -> {function.cyclomatic_after}")
        lines.append(f"Nesting      {function.nesting_before} -> {function.nesting_after}")
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    return lines


def _format_function_label(file_audit: FileAudit, function: FunctionAudit) -> str:
    # Strip the synthetic module prefix so the output reads like file: function.
    module = Path(file_audit.path).stem
    qualname = function.qualname
    prefix = f"{module}."
    if qualname.startswith(prefix):
        qualname = qualname[len(prefix) :]
    return f"{file_audit.path}: {qualname}"


def _render_hotspots(audit: Audit) -> list[str]:
    lines = ["## Review hotspots"]
    files = sorted(
        audit.files,
        key=lambda file_audit: (
            -(file_audit.hotspot.score if file_audit.hotspot else 0),
            -((file_audit.loc_added or 0) + (file_audit.loc_deleted or 0)),
            file_audit.path,
        ),
    )
    if not files:
        lines.append("No hotspots")
        return lines
    for file_audit in files[:5]:
        hotspot = file_audit.hotspot
        if not hotspot:
            continue
        lines.append(f"{hotspot.severity:<5} {file_audit.path}")
        if hotspot.reasons:
            lines.append(f"      {' · '.join(hotspot.reasons)}")
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    return lines


def render_markdown(audit: Audit) -> str:
    sections = [
        "# PR Audit",
        "",
        *_render_scope(audit),
        "",
        *_group_dependency_changes(audit.dependencies),
        "",
        *_render_tests(audit),
        "",
        *_render_complexity(audit),
        "",
        *_render_hotspots(audit),
    ]
    return "\n".join(sections).rstrip() + "\n"
