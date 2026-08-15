from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


@dataclass
class TempRepo:
    root: Path

    @classmethod
    def create(cls) -> "TempRepo":
        root = Path(tempfile.mkdtemp(prefix="pr-audit-"))
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "a@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
        return cls(root=root)

    def write_text(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_bytes(self, relative: str, data: bytes) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def remove(self, relative: str) -> None:
        path = self.root / relative
        if path.exists():
            path.unlink()

    def rename(self, source: str, target: str) -> None:
        source_path = self.root / source
        target_path = self.root / target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.rename(target_path)

    def commit(self, message: str) -> str:
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=self.root, check=True)
        return self.rev_parse("HEAD")

    def rev_parse(self, ref: str) -> str:
        completed = subprocess.run(["git", "rev-parse", ref], cwd=self.root, check=True, capture_output=True, text=True)
        return completed.stdout.strip()

    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return subprocess.run(
            ["python3", "-m", "pr_audit", *args],
            cwd=cwd or self.root,
            env=env,
            capture_output=True,
            text=True,
        )
