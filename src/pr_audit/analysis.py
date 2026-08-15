from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .analyzers import analyze_changed_python_file, analyze_dependency_file, analyze_python_structure, classify_path, summarize_scope, summarize_tests
from .errors import PrAuditError
from .git import collect_changed_files, collect_hunks_for_file, git_toplevel, show_blob_text, validate_ref
from .models import AnalyzerError, Audit, DependencyChange, FileAudit, Metadata, StructureMetrics, Summary
from .scoring import score_hotspots


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _changed_path_for_classification(file_audit: FileAudit) -> str:
    if file_audit.status == "deleted" and file_audit.renamed_from:
        return file_audit.renamed_from
    return file_audit.path


def analyze_repo(repo_root: Path, base_ref: str, head_ref: str, *, generated_at: str | None = None) -> Audit:
    validate_ref(repo_root, base_ref)
    validate_ref(repo_root, head_ref)

    changed_files = collect_changed_files(repo_root, base_ref, head_ref)
    scope = summarize_scope(changed_files)
    tests = summarize_tests(changed_files)

    files: list[FileAudit] = []
    dependencies: list[DependencyChange] = []
    errors: list[AnalyzerError] = []
    structure = StructureMetrics()

    for changed_file in changed_files:
        path_for_category = changed_file.path if changed_file.status != "deleted" else changed_file.old_path or changed_file.path
        category = classify_path(path_for_category)
        file_audit = FileAudit(
            path=changed_file.path,
            status=changed_file.status,
            category=category,
            loc_added=changed_file.loc_added,
            loc_deleted=changed_file.loc_deleted,
            binary=changed_file.binary,
            renamed_from=changed_file.old_path if changed_file.status == "renamed" else None,
        )

        base_text = None
        head_text = None
        if not changed_file.binary:
            if changed_file.status != "added":
                base_text = show_blob_text(repo_root, base_ref, changed_file.old_path or changed_file.path, required=True)
            if changed_file.status != "deleted":
                head_text = show_blob_text(repo_root, head_ref, changed_file.path, required=True)

        if category == "dependency":
            dependency_changes, dependency_errors = analyze_dependency_file(
                path=path_for_category,
                base_text=base_text,
                head_text=head_text,
            )
            dependencies.extend(dependency_changes)
            errors.extend(dependency_errors)

        if path_for_category.endswith(".py") and not changed_file.binary:
            try:
                hunks = collect_hunks_for_file(repo_root, base_ref, head_ref, changed_file)
                file_audit.functions = analyze_changed_python_file(
                    changed_file,
                    base_text=base_text,
                    head_text=head_text,
                    hunks=hunks,
                )
            except SyntaxError as exc:
                file_audit.analysis_error = str(exc)
                errors.append(AnalyzerError(area="functions", path=path_for_category, message=str(exc)))
            else:
                if category == "production":
                    try:
                        file_audit.structure = analyze_python_structure(
                            changed_file,
                            base_text=base_text,
                            head_text=head_text,
                        )
                    except SyntaxError as exc:
                        file_audit.analysis_error = str(exc)
                        errors.append(AnalyzerError(area="structure", path=path_for_category, message=str(exc)))
                    else:
                        if file_audit.structure is not None:
                            if changed_file.status == "added":
                                structure.production_files_added += 1
                            elif changed_file.status == "deleted":
                                structure.production_files_deleted += 1
                            else:
                                structure.production_files_modified += 1
                            structure.classes_added += file_audit.structure.classes_added
                            structure.classes_removed += file_audit.structure.classes_removed
                            structure.functions_added += file_audit.structure.functions_added
                            structure.functions_removed += file_audit.structure.functions_removed

        files.append(file_audit)

    score_hotspots(files, dependencies)
    summary = Summary(
        changed_functions_increased=sum(
            1
            for file_audit in files
            for function in file_audit.functions
            if function.cyclomatic_before is not None
            and function.cyclomatic_after is not None
            and function.cyclomatic_after > function.cyclomatic_before
        ),
        hotspot_count=sum(1 for file_audit in files if file_audit.hotspot and file_audit.hotspot.score > 0),
    )
    return Audit(
        metadata=Metadata(base_ref=base_ref, head_ref=head_ref, generated_at=generated_at or _utc_now()),
        scope=scope,
        dependencies=dependencies,
        tests=tests,
        structure=structure,
        files=files,
        summary=summary,
        errors=errors,
    )
