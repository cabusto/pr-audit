from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from ..models import AnalyzerError, DependencyChange


_DEV_GROUP_NAMES = {"dev", "test", "tests", "lint", "type", "typing", "ci", "docs"}
_DEV_MARKERS = {"dev", "test", "tests", "lint", "type", "typing", "ci", "docs"}
_LOCK_MANIFEST_NAMES = {"poetry.lock", "pipfile", "pipfile.lock", "uv.lock"}
_REQUIREMENTS_SUFFIXES = (".txt", ".in", ".lock")
_REQ_NAME_RE = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9_.-]*)(?P<extras>\[[^\]]+\])?(?P<rest>.*)$")


@dataclass(slots=True)
class _DependencyRecord:
    key: str
    name: str
    specifier: str
    dependency_type: str
    manifest: str
    section: str


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _path_tokens(path: str) -> set[str]:
    tokens: set[str] = set()
    for part in PurePosixPath(path.lower()).parts:
        tokens.update(token for token in re.split(r"[^a-z0-9]+", part) if token)
    return tokens


def is_dependency_manifest(path: str) -> bool:
    lowered = PurePosixPath(path.lower())
    name = lowered.name
    if name == "pyproject.toml":
        return True
    if name in _LOCK_MANIFEST_NAMES:
        return True
    if (name.startswith("requirements") or "requirements" in lowered.parts) and name.endswith(_REQUIREMENTS_SUFFIXES):
        return True
    return False


def _supports_dependency_parsing(path: str) -> bool:
    lowered = PurePosixPath(path.lower())
    name = lowered.name
    if name == "pyproject.toml":
        return True
    return (name.startswith("requirements") or "requirements" in lowered.parts) and name.endswith(_REQUIREMENTS_SUFFIXES)


def _normalize_extras(extras: str | None) -> str:
    if not extras:
        return ""
    values = sorted(_normalize_name(value.strip()) for value in extras[1:-1].split(",") if value.strip())
    return f"[{','.join(values)}]" if values else ""


def _parse_requirement_line(line: str, *, manifest: str, section: str, dependency_type: str) -> _DependencyRecord | None:
    stripped = re.sub(r"\s+#.*$", "", line).strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("-"):
        return None
    match = _REQ_NAME_RE.match(stripped)
    if not match:
        return _DependencyRecord(
            key=stripped.lower(),
            name=stripped,
            specifier="",
            dependency_type=dependency_type,
            manifest=manifest,
            section=section,
        )
    name = _normalize_name(match.group("name"))
    extras = _normalize_extras(match.group("extras"))
    specifier = match.group("rest").strip()
    key = f"{name}{extras}"
    return _DependencyRecord(
        key=key,
        name=key,
        specifier=specifier,
        dependency_type=dependency_type,
        manifest=manifest,
        section=section,
    )


def _parse_requirement_list(items: list[str], *, manifest: str, section: str, dependency_type: str) -> dict[str, _DependencyRecord]:
    records: dict[str, _DependencyRecord] = {}
    for item in items:
        record = _parse_requirement_line(item, manifest=manifest, section=section, dependency_type=dependency_type)
        if record:
            records[record.key] = record
    return records


def _stringify_poetry_value(value: Any) -> tuple[str, str]:
    if isinstance(value, str):
        return value.strip(), "runtime"
    if isinstance(value, dict):
        pieces: list[str] = []
        dependency_type = "runtime"
        version = value.get("version")
        if version:
            pieces.append(f"version={version}")
        extras = value.get("extras")
        if extras:
            pieces.append("extras=" + ",".join(sorted(str(item).strip() for item in extras)))
        markers = value.get("markers")
        if markers:
            pieces.append(f"markers={markers}")
        if value.get("optional"):
            dependency_type = "optional"
            pieces.append("optional=true")
        if value.get("allow-prereleases"):
            pieces.append("allow-prereleases=true")
        if value.get("python"):
            pieces.append(f"python={value['python']}")
        return ";".join(pieces), dependency_type
    return str(value).strip(), "unknown"


def _poetry_group_type(group: str) -> str:
    return "development" if group in _DEV_GROUP_NAMES or group.startswith("dev") else "unknown"


def _requirements_dependency_type(manifest: str) -> str:
    if _path_tokens(manifest) & _DEV_MARKERS:
        return "development"
    return "runtime"


def _table(value: Any, where: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be a table")
    return value


def _string_list(value: Any, where: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{where} must be a list of strings")
    return value


def _parse_pyproject(text: str, *, manifest: str) -> dict[str, _DependencyRecord]:
    data = tomllib.loads(text)
    records: dict[str, _DependencyRecord] = {}

    project = _table(data.get("project"), "project")
    for item in _string_list(project.get("dependencies"), "project.dependencies"):
        record = _parse_requirement_line(item, manifest=manifest, section="project.dependencies", dependency_type="runtime")
        if record:
            records[f"project.dependencies::{record.key}"] = record

    optional = _table(project.get("optional-dependencies"), "project.optional-dependencies")
    for group, items in optional.items():
        for item in _string_list(items, f"project.optional-dependencies.{group}"):
            record = _parse_requirement_line(
                item,
                manifest=manifest,
                section=f"project.optional-dependencies.{group}",
                dependency_type="optional",
            )
            if record:
                records[f"project.optional-dependencies.{group}::{record.key}"] = record

    tool = _table(data.get("tool"), "tool")
    poetry = _table(tool.get("poetry"), "tool.poetry")
    for name, value in _table(poetry.get("dependencies"), "tool.poetry.dependencies").items():
        if name == "python":
            continue
        specifier, dependency_type = _stringify_poetry_value(value)
        key = _normalize_name(name)
        records[f"tool.poetry.dependencies::{key}"] = _DependencyRecord(
            key=f"tool.poetry.dependencies::{key}",
            name=key,
            specifier=specifier,
            dependency_type=dependency_type,
            manifest=manifest,
            section="tool.poetry.dependencies",
        )

    groups = _table(poetry.get("group"), "tool.poetry.group")
    for group, group_data in groups.items():
        dependency_type = _poetry_group_type(group)
        group_table = _table(group_data, f"tool.poetry.group.{group}")
        for name, value in _table(group_table.get("dependencies"), f"tool.poetry.group.{group}.dependencies").items():
            if name == "python":
                continue
            specifier, value_type = _stringify_poetry_value(value)
            key = _normalize_name(name)
            records[f"tool.poetry.group.{group}.dependencies::{key}"] = _DependencyRecord(
                key=f"tool.poetry.group.{group}.dependencies::{key}",
                name=key,
                specifier=specifier,
                dependency_type=value_type if value_type != "runtime" else dependency_type,
                manifest=manifest,
                section=f"tool.poetry.group.{group}.dependencies",
            )

    return records


def _parse_requirements(text: str, *, manifest: str) -> dict[str, _DependencyRecord]:
    records: dict[str, _DependencyRecord] = {}
    for line in text.splitlines():
        record = _parse_requirement_line(
            line,
            manifest=manifest,
            section=PurePosixPath(manifest).name,
            dependency_type=_requirements_dependency_type(manifest),
        )
        if record:
            records[record.key] = record
    return records


def _records_from_text(text: str | None, *, manifest: str) -> dict[str, _DependencyRecord] | None:
    if text is None:
        return {}
    name = PurePosixPath(manifest).name
    if name == "pyproject.toml":
        return _parse_pyproject(text, manifest=manifest)
    if _supports_dependency_parsing(manifest):
        return _parse_requirements(text, manifest=manifest)
    return None


def _diff_records(
    base_records: dict[str, _DependencyRecord],
    head_records: dict[str, _DependencyRecord],
) -> list[DependencyChange]:
    changes: list[DependencyChange] = []
    for key in sorted(set(base_records) | set(head_records)):
        base = base_records.get(key)
        head = head_records.get(key)
        if base and not head:
            changes.append(
                DependencyChange(
                    name=base.name,
                    status="removed",
                    before=base.specifier or None,
                    after=None,
                    dependency_type=base.dependency_type,
                    manifest=base.manifest,
                    section=base.section,
                )
            )
        elif head and not base:
            changes.append(
                DependencyChange(
                    name=head.name,
                    status="added",
                    before=None,
                    after=head.specifier or None,
                    dependency_type=head.dependency_type,
                    manifest=head.manifest,
                    section=head.section,
                )
            )
        elif base and head and (base.specifier != head.specifier or base.dependency_type != head.dependency_type):
            changes.append(
                DependencyChange(
                    name=head.name,
                    status="changed",
                    before=base.specifier or None,
                    after=head.specifier or None,
                    dependency_type=head.dependency_type,
                    manifest=head.manifest,
                    section=head.section,
                )
            )
    return changes


def analyze_dependency_file(
    *,
    path: str,
    base_text: str | None,
    head_text: str | None,
) -> tuple[list[DependencyChange], list[AnalyzerError]]:
    if not _supports_dependency_parsing(path):
        return [], [AnalyzerError(area="dependencies", path=path, message=f"unsupported dependency manifest format: {path}")]
    try:
        base_records = _records_from_text(base_text, manifest=path)
    except ValueError as exc:  # includes tomllib.TOMLDecodeError
        return [], [AnalyzerError(area="dependencies", path=path, message=str(exc))]
    try:
        head_records = _records_from_text(head_text, manifest=path)
    except ValueError as exc:  # includes tomllib.TOMLDecodeError
        return [], [AnalyzerError(area="dependencies", path=path, message=str(exc))]
    return _diff_records(base_records or {}, head_records or {}), []
