"""Exercise the file-size policy against real, isolated Git histories."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_large_files import MAX_FILE_BYTES, find_oversized_blobs


class LargeFileChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jev-git-policy-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Policy test fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "base", "--allow-empty")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True, capture_output=True, text=True,
        ).stdout

    def write_and_commit(self, path, size):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x" * size)
        self.git("add", "--", path)
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture change")

    def check(self, base=None):
        return find_oversized_blobs(self.repo, base_ref=base, limit_bytes=64)

    def test_default_limit_is_ten_mib(self):
        self.assertEqual(MAX_FILE_BYTES, 10 * 1024 * 1024)

    def test_exact_boundary_is_allowed(self):
        self.write_and_commit("fixture.dat", 64)
        self.assertEqual(self.check(), [])

    def test_larger_tracked_blob_fails_with_path_and_size(self):
        self.write_and_commit("fixture.dat", 65)
        failures = self.check()
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].size, 65)
        self.assertIn("fixture.dat", failures[0].paths)

    def test_untracked_and_uncommitted_content_is_not_a_git_blob(self):
        self.write_and_commit("tracked.txt", 8)
        (self.repo / "untracked.bin").write_bytes(b"x" * 100)
        (self.repo / "tracked.txt").write_bytes(b"x" * 100)
        self.assertEqual(self.check(), [])

    def test_large_blob_added_then_deleted_in_pr_still_fails(self):
        self.write_and_commit("removed.bin", 65)
        oid = self.git("rev-parse", "HEAD:removed.bin").strip()
        self.git("rm", "-q", "removed.bin")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "remove fixture")
        self.assertEqual(self.check(), [])
        failures = self.check(self.base)
        self.assertEqual([f.oid for f in failures], [oid])

    def test_replacing_large_blob_with_small_one_still_fails(self):
        self.write_and_commit("changed.bin", 65)
        self.write_and_commit("changed.bin", 8)
        self.assertEqual(len(self.check(self.base)), 1)

    def test_old_deleted_history_outside_pr_is_not_rejected(self):
        self.write_and_commit("old.bin", 65)
        self.git("rm", "-q", "old.bin")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "remove old blob")
        base = self.git("rev-parse", "HEAD").strip()
        self.write_and_commit("new.txt", 8)
        self.assertEqual(self.check(base), [])

    def test_spaces_tabs_and_newlines_in_filename(self):
        name = "folder/file with\ttab and\nnewline.bin"
        self.write_and_commit(name, 65)
        self.assertEqual(self.check()[0].paths, (name,))

    def test_same_large_blob_in_head_and_history_is_reported_once(self):
        self.write_and_commit("first.bin", 65)
        self.git("mv", "first.bin", "renamed.bin")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "rename fixture")
        self.assertEqual(len(self.check(self.base)), 1)

    def test_invalid_base_fails_closed(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.check("missing-base-ref")

    def test_cli_rejects_file_above_real_ten_mib_limit(self):
        self.write_and_commit("oversized.bin", MAX_FILE_BYTES + 1)
        script = Path(__file__).resolve().parents[1] / "scripts/check_large_files.py"
        result = subprocess.run(
            [sys.executable, str(script)], cwd=self.repo, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("oversized.bin", result.stdout)

    def test_cli_invalid_base_is_an_error_not_a_pass(self):
        script = Path(__file__).resolve().parents[1] / "scripts/check_large_files.py"
        result = subprocess.run(
            [sys.executable, str(script), "--base-ref", "missing-base-ref"],
            cwd=self.repo, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("failing closed", result.stdout)


if __name__ == "__main__":
    unittest.main()
