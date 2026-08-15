from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from helpers import TempRepo
from pr_audit.git.diff import collect_changed_files, collect_hunks_for_file


class DiffTests(unittest.TestCase):
    def test_changed_files_cover_add_modify_delete_rename_and_binary(self) -> None:
        repo = TempRepo.create()
        repo.write_text("src/app.py", "def f():\n    return 1\n")
        repo.write_text("src/delete_me.py", "x = 1\n")
        repo.write_text("src/old_name.py", "def g():\n    value = 2\n    return value\n")
        repo.write_text("tests/test_app.py", "def test_ok():\n    assert True\n")
        base = repo.commit("base")

        repo.write_text("src/app.py", "def f():\n    if True:\n        return 2\n    return 1\n")
        repo.remove("src/delete_me.py")
        repo.rename("src/old_name.py", "src/new_name.py")
        repo.write_text(
            "src/new_name.py",
            "def g():\n    value = 2\n    value += 1\n    return value\n",
        )
        repo.write_bytes("assets/blob.bin", b"\x00\x01\x02\x03")
        repo.write_text("tests/test_app.py", "def test_ok():\n    assert True\n\n")
        head = repo.commit("head")

        changed_files = collect_changed_files(repo.root, base, head)
        by_path = {changed_file.path: changed_file for changed_file in changed_files}

        self.assertEqual(by_path["src/app.py"].status, "modified")
        self.assertEqual(by_path["src/app.py"].loc_added, 2)
        self.assertEqual(by_path["src/app.py"].loc_deleted, 0)
        self.assertEqual(by_path["src/delete_me.py"].status, "deleted")
        self.assertEqual(by_path["src/delete_me.py"].loc_deleted, 1)
        self.assertEqual(by_path["src/new_name.py"].status, "renamed")
        self.assertEqual(by_path["src/new_name.py"].old_path, "src/old_name.py")
        self.assertTrue(by_path["assets/blob.bin"].binary)
        self.assertIsNone(by_path["assets/blob.bin"].loc_added)
        self.assertIsNone(by_path["assets/blob.bin"].loc_deleted)

        rename_hunks = collect_hunks_for_file(repo.root, base, head, by_path["src/new_name.py"])
        self.assertTrue(rename_hunks)
        self.assertEqual(collect_hunks_for_file(repo.root, base, head, by_path["assets/blob.bin"]), [])
