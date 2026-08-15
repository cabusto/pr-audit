from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..errors import GitCommandError, InvalidGitRefError


@dataclass(slots=True)
class ChangedFile:
    path: str
    old_path: str | None
    status: str
    loc_added: int | None
    loc_deleted: int | None
    binary: bool


@dataclass(slots=True)
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int


@dataclass(slots=True)
class _NameStatusRecord:
    status_code: str
    status: str
    path: str
    old_path: str | None
    path_count: int


@dataclass(slots=True)
class _NumstatRecord:
    added: int | None
    deleted: int | None
    paths: list[str]


HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "-C", str(repo_root), *args]
    return subprocess.run(command, check=False, capture_output=True)


def _decode_token(data: bytes) -> str:
    return data.decode("utf-8", "surrogateescape")


def validate_ref(repo_root: Path, ref: str) -> None:
    command = ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise InvalidGitRefError(ref, completed.stderr.strip() or f"Invalid git ref: {ref}")


def _parse_name_status(blob: bytes) -> list[_NameStatusRecord]:
    tokens = blob.split(b"\0")
    records: list[_NameStatusRecord] = []
    i = 0
    while i < len(tokens):
        if not tokens[i]:
            i += 1
            continue
        status_code = _decode_token(tokens[i])
        i += 1
        if status_code[0] in {"R", "C"}:
            old_path = _decode_token(tokens[i])
            path = _decode_token(tokens[i + 1])
            i += 2
            path_count = 2
        else:
            old_path = None
            path = _decode_token(tokens[i])
            i += 1
            path_count = 1
        status = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "T": "modified",
            "U": "modified",
        }.get(status_code[0], "modified")
        records.append(_NameStatusRecord(status_code, status, path, old_path, path_count))
    return records


def _parse_numstat(blob: bytes, path_counts: list[int]) -> list[_NumstatRecord]:
    tokens = blob.split(b"\0")
    records: list[_NumstatRecord] = []
    i = 0
    for path_count in path_counts:
        while i < len(tokens) and not tokens[i]:
            i += 1
        if i >= len(tokens):
            break
        count_token = _decode_token(tokens[i])
        i += 1
        parts = count_token.split("\t")
        if len(parts) < 2:
            break
        added_s, deleted_s = parts[0], parts[1]
        added = None if added_s == "-" else int(added_s)
        deleted = None if deleted_s == "-" else int(deleted_s)
        paths: list[str] = []
        embedded_path = parts[2] if len(parts) > 2 else ""
        if path_count == 1 and embedded_path:
            paths.append(embedded_path)
        else:
            for _ in range(path_count):
                while i < len(tokens) and not tokens[i]:
                    i += 1
                if i >= len(tokens):
                    break
                paths.append(_decode_token(tokens[i]))
                i += 1
        records.append(_NumstatRecord(added, deleted, paths))
    return records


def collect_changed_files(repo_root: Path, base_ref: str, head_ref: str) -> list[ChangedFile]:
    name_status = _run_git(
        repo_root,
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies",
        f"{base_ref}...{head_ref}",
        "--",
    )
    if name_status.returncode != 0:
        command = ["git", "-C", str(repo_root), "diff", "--name-status", "-z", "--find-renames", "--find-copies", f"{base_ref}...{head_ref}", "--"]
        raise GitCommandError(command, name_status.stderr.decode("utf-8", "replace"))

    numstat = _run_git(
        repo_root,
        "diff",
        "--numstat",
        "-z",
        "--find-renames",
        "--find-copies",
        f"{base_ref}...{head_ref}",
        "--",
    )
    if numstat.returncode != 0:
        command = ["git", "-C", str(repo_root), "diff", "--numstat", "-z", "--find-renames", "--find-copies", f"{base_ref}...{head_ref}", "--"]
        raise GitCommandError(command, numstat.stderr.decode("utf-8", "replace"))

    status_records = _parse_name_status(name_status.stdout)
    numstat_records = _parse_numstat(numstat.stdout, [record.path_count for record in status_records])
    if len(status_records) != len(numstat_records):
        raise GitCommandError(
            ["git", "-C", str(repo_root), "diff", "--name-status/--numstat", f"{base_ref}...{head_ref}"],
            "diff metadata counts did not align",
        )

    changed_files: list[ChangedFile] = []
    for status_record, numstat_record in zip(status_records, numstat_records, strict=True):
        changed_files.append(
            ChangedFile(
                path=status_record.path,
                old_path=status_record.old_path,
                status=status_record.status,
                loc_added=numstat_record.added,
                loc_deleted=numstat_record.deleted,
                binary=numstat_record.added is None or numstat_record.deleted is None,
            )
        )
    return changed_files


def collect_hunks_for_file(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
    changed_file: ChangedFile,
) -> list[DiffHunk]:
    if changed_file.status == "deleted":
        paths = [changed_file.old_path or changed_file.path]
    elif changed_file.status in {"renamed", "copied"}:
        paths = [changed_file.old_path or changed_file.path, changed_file.path]
    else:
        paths = [changed_file.path]

    command = [
        "git",
        "-C",
        str(repo_root),
        "diff",
        "--unified=0",
        "--no-color",
        "--find-renames",
        "--find-copies",
        f"{base_ref}...{head_ref}",
        "--",
        *paths,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise GitCommandError(command, completed.stderr)

    hunks: list[DiffHunk] = []
    for line in completed.stdout.splitlines():
        match = HUNK_RE.match(line)
        if not match:
            continue
        old_count = int(match.group("old_count") or "1")
        new_count = int(match.group("new_count") or "1")
        hunks.append(
            DiffHunk(
                old_start=int(match.group("old_start")),
                old_count=old_count,
                new_start=int(match.group("new_start")),
                new_count=new_count,
            )
        )
    return hunks
