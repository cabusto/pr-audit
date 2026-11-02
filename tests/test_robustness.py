from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import TempRepo
from pr_audit.analysis import analyze_repo
from pr_audit.errors import PrAuditError
from pr_audit.render import render_markdown


GENERATED_AT = "2024-01-01T00:00:00Z"


def _git(repo: TempRepo, *args: str | bytes, stdin: bytes | None = None) -> str:
    completed = subprocess.run(["git", *args], cwd=repo.root, check=True, capture_output=True, input=stdin)
    return completed.stdout.decode().strip()


def _commit_index(repo: TempRepo, message: str) -> str:
    """Commit the index as-is, for entries that can't exist in the working tree."""
    _git(repo, "commit", "-q", "-m", message)
    return repo.rev_parse("HEAD")


class RobustnessTests(unittest.TestCase):
    def test_base_branch_moved_after_branch_point(self) -> None:
        repo = TempRepo.create()
        repo.write_text("src/a.py", "def f():\n    return 1\n")
        repo.write_text("src/b.py", "def g():\n    return 1\n")
        repo.commit("base")
        _git(repo, "branch", "-M", "main")
        _git(repo, "checkout", "-q", "-b", "feature")
        repo.write_text("src/a.py", "def f():\n    if True:\n        return 2\n    return 1\n")
        feature = repo.commit("feature edits a.py")
        _git(repo, "checkout", "-q", "main")
        repo.remove("src/a.py")
        repo.commit("main deletes a.py")

        audit = analyze_repo(repo.root, "main", feature, generated_at=GENERATED_AT)

        self.assertEqual([file.path for file in audit.files], ["src/a.py"])
        function = audit.files[0].functions[0]
        self.assertEqual((function.cyclomatic_before, function.cyclomatic_after), (1, 2))

    def test_non_utf8_files_do_not_abort(self) -> None:
        repo = TempRepo.create()
        repo.write_text("src/app.py", "def f():\n    return 1\n")
        base = repo.commit("base")
        repo.write_bytes("data/prices.csv", "café,1\n".encode("latin-1"))
        repo.write_bytes("src/legacy.py", "# -*- coding: latin-1 -*-\ndef f():\n    return 'café'\n".encode("latin-1"))
        repo.write_bytes("src/broken.py", b"def f():\n    return '\xff'\n")
        head = repo.commit("head")

        audit = analyze_repo(repo.root, base, head, generated_at=GENERATED_AT)

        files = {file.path: file for file in audit.files}
        self.assertEqual(set(files), {"data/prices.csv", "src/legacy.py", "src/broken.py"})
        self.assertEqual([function.qualname for function in files["src/legacy.py"].functions], ["legacy.f"])
        self.assertIn("unable to decode", files["src/broken.py"].analysis_error)
        self.assertEqual([error.path for error in audit.errors], ["src/broken.py"])

    def test_submodule_change_does_not_abort(self) -> None:
        repo = TempRepo.create()
        repo.write_text("README.md", "hi\n")
        base = repo.commit("base")
        _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{base},vendor/lib")
        head = _commit_index(repo, "add submodule")

        audit = analyze_repo(repo.root, base, head, generated_at=GENERATED_AT)

        self.assertEqual([file.path for file in audit.files], ["vendor/lib"])
        self.assertFalse(audit.errors)

    def test_cli_handles_non_utf8_filename(self) -> None:
        repo = TempRepo.create()
        repo.write_text("README.md", "hi\n")
        base = repo.commit("base")
        blob = _git(repo, "hash-object", "-w", "--stdin", stdin=b"x\n")
        _git(repo, "update-index", "--add", "--cacheinfo", "100644", blob, b"caf\xe9.txt")
        head = _commit_index(repo, "add latin-1 filename")

        result = repo.run_cli("analyze", "--base", base, "--head", head)

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((repo.root / "audit.json").read_text(encoding="utf-8"))
        self.assertEqual(data["scope"]["files_changed"], 1)

    def test_malformed_pyproject_types_are_reported(self) -> None:
        cases = {
            "string dependencies": '[project]\ndependencies = "requests"\n',
            "poetry group list": '[tool.poetry]\ngroup = ["dev"]\n',
        }
        for label, text in cases.items():
            with self.subTest(label):
                repo = TempRepo.create()
                repo.write_text("pyproject.toml", "[project]\nname = \"x\"\n")
                base = repo.commit("base")
                repo.write_text("pyproject.toml", text)
                head = repo.commit("head")

                audit = analyze_repo(repo.root, base, head, generated_at=GENERATED_AT)

                self.assertEqual(audit.dependencies, [])
                self.assertEqual([error.area for error in audit.errors], ["dependencies"])

    def test_shallow_clone_error_says_how_to_fix(self) -> None:
        repo = TempRepo.create()
        repo.write_text("src/a.py", "def f():\n    return 1\n")
        base = repo.commit("base")
        repo.write_text("src/a.py", "def f():\n    return 2\n")
        repo.commit("head")
        shallow = TempRepo(root=repo.root.parent / f"{repo.root.name}-shallow")
        subprocess.run(["git", "clone", "-q", "--depth", "1", repo.root.as_uri(), str(shallow.root)], check=True)

        with self.assertRaisesRegex(PrAuditError, "shallow clone.*fetch-depth: 0"):
            analyze_repo(shallow.root, base, "HEAD", generated_at=GENERATED_AT)

    def test_markdown_paths_cannot_escape_code_block(self) -> None:
        repo = TempRepo.create()
        repo.write_text("README.md", "x\n")
        base = repo.commit("base")
        repo.write_text("docs/```@team [x](evil.example).md", "x\n")
        head = repo.commit("head")

        markdown = render_markdown(analyze_repo(repo.root, base, head, generated_at=GENERATED_AT))

        hotspots = markdown[markdown.index("## Review hotspots"):].splitlines()
        self.assertEqual(hotspots[1], "````text")
        self.assertEqual(hotspots[-1], "````")
        self.assertIn("@team [x](evil.example)", hotspots[2])


if __name__ == "__main__":
    unittest.main()
