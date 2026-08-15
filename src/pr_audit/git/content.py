from __future__ import annotations

import subprocess
from pathlib import Path

from ..errors import GitCommandError


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "-C", str(repo_root), *args]
    return subprocess.run(command, check=False, capture_output=True)


def git_toplevel(cwd: Path) -> Path:
    command = ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise GitCommandError(command, completed.stderr)
    return Path(completed.stdout.strip())


def show_blob_text(repo_root: Path, ref: str, path: str, *, required: bool = True) -> str | None:
    command = ["git", "-C", str(repo_root), "show", f"{ref}:{path}"]
    completed = _run_git(repo_root, "show", f"{ref}:{path}")
    if completed.returncode != 0:
        if not required:
            return None
        raise GitCommandError(command, completed.stderr.decode("utf-8", "replace"))
    try:
        return completed.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        if not required:
            return None
        raise GitCommandError(command, f"unable to decode {path} at {ref}: {exc}") from exc
