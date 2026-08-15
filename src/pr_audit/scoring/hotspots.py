from __future__ import annotations

from math import ceil

from ..models import DependencyChange, FileAudit, Hotspot


def _reason(reason_type: str, value: object | None = None) -> dict[str, object]:
    reason: dict[str, object] = {"type": reason_type}
    if value is not None:
        reason["value"] = value
    return reason


def score_hotspots(files: list[FileAudit], dependencies: list[DependencyChange]) -> None:
    dependency_bonus = {
        change.manifest: 0
        for change in dependencies
        if change.status == "added" and change.dependency_type == "runtime"
    }
    for change in dependencies:
        if change.status == "added" and change.dependency_type == "runtime":
            dependency_bonus[change.manifest] += 1

    scored: list[tuple[int, int, str, FileAudit, int, int, int, int]] = []
    largest_production_loc_changed = 0
    for file_audit in files:
        loc_added = file_audit.loc_added or 0
        loc_deleted = file_audit.loc_deleted or 0
        production_loc_changed = 0
        if file_audit.category == "production" and file_audit.loc_added is not None and file_audit.loc_deleted is not None:
            production_loc_changed = loc_added + loc_deleted
        cyclomatic_delta = sum(
            max(0, (function.cyclomatic_after or 0) - (function.cyclomatic_before or 0))
            for function in file_audit.functions
            if function.cyclomatic_after is not None and function.cyclomatic_before is not None
        )
        nesting_delta = max(
            [max(0, (function.nesting_after or 0) - (function.nesting_before or 0)) for function in file_audit.functions if function.nesting_after is not None and function.nesting_before is not None],
            default=0,
        )
        dependency_count = dependency_bonus.get(file_audit.path, 0) if file_audit.category == "dependency" else 0
        dependency_points = dependency_count * 50
        score = production_loc_changed + cyclomatic_delta * 20 + nesting_delta * 30 + dependency_points
        scored.append((score, loc_added + loc_deleted, file_audit.path, file_audit, production_loc_changed, cyclomatic_delta, nesting_delta, dependency_count))
        if file_audit.category == "production":
            largest_production_loc_changed = max(largest_production_loc_changed, production_loc_changed)

    for score, _, _, file_audit, production_loc_changed, cyclomatic_delta, nesting_delta, dependency_count in scored:
        reasons: list[dict[str, object]] = []
        if file_audit.loc_added is not None or file_audit.loc_deleted is not None:
            added = file_audit.loc_added or 0
            deleted = file_audit.loc_deleted or 0
            if added or deleted:
                reasons.append(_reason("loc_changed", {"added": added, "deleted": deleted}))
        if file_audit.category == "production" and file_audit.status == "added":
            reasons.append(_reason("production_file_added"))
        if file_audit.category == "production" and production_loc_changed > 0 and production_loc_changed == largest_production_loc_changed:
            reasons.append(_reason("largest_production_change"))
        if cyclomatic_delta > 0:
            reasons.append(_reason("complexity_increase", cyclomatic_delta))
        if nesting_delta > 0:
            reasons.append(_reason("nesting_increase", nesting_delta))
        if dependency_count > 0:
            reasons.append(_reason("runtime_dependency_added", dependency_count))
        if file_audit.category == "tests":
            reasons.append(_reason("test_only"))
        elif file_audit.category == "docs":
            reasons.append(_reason("docs_only"))
        elif file_audit.category == "config":
            reasons.append(_reason("config_only"))
        elif file_audit.category == "dependency":
            reasons.append(_reason("dependency_manifest"))
        elif file_audit.category == "other":
            reasons.append(_reason("other"))
        file_audit.hotspot = Hotspot(score=score, severity="LOW", reasons=reasons)

    positive = [item for item in scored if item[0] > 0]
    positive.sort(key=lambda item: (-item[0], -item[1], item[2]))
    positive_count = len(positive)
    if positive_count:
        high_cutoff = max(1, ceil(positive_count * 0.2))
        medium_cutoff = ceil(positive_count * 0.5)
        for index, (_, _, _, file_audit, _, _, _, _) in enumerate(positive, start=1):
            if index <= high_cutoff:
                file_audit.hotspot.severity = "HIGH"
            elif index <= medium_cutoff:
                file_audit.hotspot.severity = "MED"
            else:
                file_audit.hotspot.severity = "LOW"

    for _, _, _, file_audit, _, _, _, _ in scored:
        if file_audit.hotspot.score == 0:
            file_audit.hotspot.severity = "LOW"
