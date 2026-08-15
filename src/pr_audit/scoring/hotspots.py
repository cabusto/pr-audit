from __future__ import annotations

from math import ceil

from ..models import DependencyChange, FileAudit, Hotspot


def _format_loc(file_audit: FileAudit) -> str | None:
    if file_audit.loc_added is None or file_audit.loc_deleted is None:
        return None
    if file_audit.loc_added and file_audit.loc_deleted:
        return f"+{file_audit.loc_added:,} / -{file_audit.loc_deleted:,} LOC"
    if file_audit.loc_added:
        return f"+{file_audit.loc_added:,} LOC"
    if file_audit.loc_deleted:
        return f"-{file_audit.loc_deleted:,} LOC"
    return None


def score_hotspots(files: list[FileAudit], dependencies: list[DependencyChange]) -> None:
    dependency_bonus = {
        change.manifest: 0
        for change in dependencies
        if change.status == "added" and change.dependency_type == "runtime"
    }
    for change in dependencies:
        if change.status == "added" and change.dependency_type == "runtime":
            dependency_bonus[change.manifest] += 1

    scored: list[tuple[int, int, str, FileAudit]] = []
    for file_audit in files:
        production_loc_changed = 0
        if file_audit.category == "production" and file_audit.loc_added is not None and file_audit.loc_deleted is not None:
            production_loc_changed = file_audit.loc_added + file_audit.loc_deleted
        cyclomatic_delta = sum(
            max(0, (function.cyclomatic_after or 0) - (function.cyclomatic_before or 0))
            for function in file_audit.functions
            if function.cyclomatic_after is not None and function.cyclomatic_before is not None
        )
        nesting_delta = max(
            [max(0, (function.nesting_after or 0) - (function.nesting_before or 0)) for function in file_audit.functions if function.nesting_after is not None and function.nesting_before is not None],
            default=0,
        )
        dependency_points = dependency_bonus.get(file_audit.path, 0) * 50 if file_audit.category == "dependency" else 0
        score = production_loc_changed + cyclomatic_delta * 20 + nesting_delta * 30 + dependency_points
        scored.append((score, (file_audit.loc_added or 0) + (file_audit.loc_deleted or 0), file_audit.path, file_audit))
        reasons: list[str] = []
        loc_reason = _format_loc(file_audit)
        if loc_reason:
            reasons.append(loc_reason)
        if cyclomatic_delta > 0:
            reasons.append(f"complexity +{cyclomatic_delta}")
        if nesting_delta > 0:
            reasons.append(f"max nesting +{nesting_delta}")
        if dependency_points > 0:
            reasons.append(f"{dependency_bonus.get(file_audit.path, 0)} runtime dependencies added")
        if file_audit.category == "tests":
            reasons.append("test-only")
        elif file_audit.category == "docs":
            reasons.append("docs-only")
        elif file_audit.category == "config":
            reasons.append("config-only")
        elif file_audit.category == "dependency":
            reasons.append("dependency manifest")
        elif file_audit.category == "other":
            reasons.append("other")
        file_audit.hotspot = Hotspot(score=score, severity="LOW", reasons=[reason for reason in reasons if reason])

    positive = [item for item in scored if item[0] > 0]
    positive.sort(key=lambda item: (-item[0], -item[1], item[2]))
    positive_count = len(positive)
    if positive_count:
        high_cutoff = max(1, ceil(positive_count * 0.2))
        medium_cutoff = ceil(positive_count * 0.5)
        for index, (_, _, _, file_audit) in enumerate(positive, start=1):
            if index <= high_cutoff:
                file_audit.hotspot.severity = "HIGH"
            elif index <= medium_cutoff:
                file_audit.hotspot.severity = "MED"
            else:
                file_audit.hotspot.severity = "LOW"

    for _, _, _, file_audit in scored:
        if file_audit.hotspot.score == 0:
            file_audit.hotspot.severity = "LOW"
