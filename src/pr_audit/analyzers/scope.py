from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from ..git.diff import ChangedFile
from ..models import CategoryCounts, Scope, TestsMetrics


def classify_path(path: str) -> str:
    lowered = path.lower()
    posix = PurePosixPath(lowered)
    parts = posix.parts
    name = posix.name

    if name == "pyproject.toml" or name.startswith("requirements") and name.endswith(".txt"):
        return "dependency"
    if "tests" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "tests"
    if name.endswith(".md") or "docs" in parts:
        return "docs"
    if ".github" in parts or name.endswith(".toml") or name.endswith(".yaml") or name.endswith(".yml"):
        return "config"
    if name.endswith(".py"):
        return "production"
    return "other"


def summarize_scope(changed_files: list[ChangedFile]) -> Scope:
    categories = Counter()
    loc_added = 0
    loc_deleted = 0
    files_added = 0
    files_deleted = 0
    for changed_file in changed_files:
        category = classify_path(changed_file.path if changed_file.status != "deleted" else changed_file.old_path or changed_file.path)
        categories[category] += 1
        if changed_file.status == "added":
            files_added += 1
        if changed_file.status == "deleted":
            files_deleted += 1
        if changed_file.loc_added is not None:
            loc_added += changed_file.loc_added
        if changed_file.loc_deleted is not None:
            loc_deleted += changed_file.loc_deleted
    return Scope(
        loc_added=loc_added,
        loc_deleted=loc_deleted,
        files_changed=len(changed_files),
        files_added=files_added,
        files_deleted=files_deleted,
        categories=CategoryCounts(
            production=categories.get("production", 0),
            tests=categories.get("tests", 0),
            config=categories.get("config", 0),
            docs=categories.get("docs", 0),
            dependency=categories.get("dependency", 0),
            other=categories.get("other", 0),
        ),
    )


def summarize_tests(changed_files: list[ChangedFile]) -> TestsMetrics:
    test_files = [
        changed_file
        for changed_file in changed_files
        if classify_path(changed_file.path if changed_file.status != "deleted" else changed_file.old_path or changed_file.path) == "tests"
    ]
    files_changed = len(test_files)
    files_added = sum(1 for changed_file in test_files if changed_file.status == "added")
    test_loc_added = sum(changed_file.loc_added or 0 for changed_file in test_files)
    production_loc_added = sum(
        changed_file.loc_added or 0
        for changed_file in changed_files
        if classify_path(changed_file.path if changed_file.status != "deleted" else changed_file.old_path or changed_file.path) == "production"
    )
    ratio = None if test_loc_added == 0 else production_loc_added / test_loc_added
    return TestsMetrics(
        files_changed=files_changed,
        files_added=files_added,
        loc_added=test_loc_added,
        production_loc_added=production_loc_added,
        production_test_ratio=ratio,
    )
