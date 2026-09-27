import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine import backend


def _rm(p):
    def e(fn, fp, _):
        try:
            os.chmod(fp, 0o777)
            fn(fp)
        except Exception:
            pass
    shutil.rmtree(p, onerror=e)


def _mk(d):
    subprocess.run(["git", "init"], cwd=str(d), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.test"], cwd=str(d), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(d), check=True, capture_output=True)


def _sc(d, f, msg="init"):
    subprocess.run(["git", "add", "--", str(f)], cwd=str(d), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=str(d), check=True, capture_output=True)


class TestIsGitAvailable(unittest.TestCase):
    def test_two_tuple(self):
        self.assertEqual(len(backend.is_git_available()), 2)

    def test_types(self):
        ok, msg = backend.is_git_available()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)

    def test_available(self):
        ok, msg = backend.is_git_available()
        self.assertTrue(ok, msg)
        self.assertIn("git version", msg.lower())


class TestIsGitRepository(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        _rm(self.d)

    def test_valid(self):
        _mk(self.d)
        ok, msg = backend.is_git_repository(self.d)
        self.assertTrue(ok, msg)
        self.assertIn("detected", msg.lower())

    def test_plain_dir(self):
        ok, _ = backend.is_git_repository(self.d)
        self.assertFalse(ok)

    def test_empty(self):
        ok, _ = backend.is_git_repository("")
        self.assertFalse(ok)

    def test_missing(self):
        ok, _ = backend.is_git_repository(self.d / "nope")
        self.assertFalse(ok)

    def test_tuple(self):
        self.assertEqual(len(backend.is_git_repository(self.d)), 2)


class TestGitRepoRootDetection(unittest.TestCase):
    """Test Git repository root detection and subdirectories (Parts 2 & 3)."""
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        _rm(self.d)

    def test_non_git_dir_message(self):
        ok, msg, root = backend.get_git_repo_root(self.d)
        self.assertFalse(ok)
        self.assertIn("not inside a Git repository", msg)
        self.assertIsNone(root)

    def test_correct_git_root(self):
        _mk(self.d)
        ok, msg, root = backend.get_git_repo_root(self.d)
        self.assertTrue(ok, msg)
        self.assertEqual(root.resolve(), self.d.resolve())

    def test_configured_subdirectory_finds_parent_git_root(self):
        _mk(self.d)
        sub = self.d / "Arrays" / "SubFolder"
        sub.mkdir(parents=True)
        ok, msg, root = backend.get_git_repo_root(sub)
        self.assertTrue(ok, msg)
        self.assertEqual(root.resolve(), self.d.resolve())


class TestGitRemotes(unittest.TestCase):
    """Test remote detection, update without duplication, and persistence (Parts 4, 5, 6)."""
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        _mk(self.d)
        self.cfg_path = backend.get_config_path()
        self.cfg_backup = self.cfg_path.read_text(encoding="utf-8") if self.cfg_path.exists() else None

    def tearDown(self):
        _rm(self.d)
        if self.cfg_backup is not None:
            self.cfg_path.write_text(self.cfg_backup, encoding="utf-8")

    def test_no_remote_detection(self):
        ok, msg, remotes = backend.get_git_remotes(self.d)
        self.assertTrue(ok)
        self.assertEqual(remotes, {})
        self.assertIn("No Git remote", msg)

    def test_remote_add_and_detect(self):
        test_url = "https://github.com/example/dsa.git"
        ok, msg = backend.set_git_remote(self.d, test_url, "origin")
        self.assertTrue(ok, msg)

        ok2, _, remotes = backend.get_git_remotes(self.d)
        self.assertTrue(ok2)
        self.assertIn("origin", remotes)
        self.assertEqual(remotes["origin"], test_url)

    def test_remote_update_without_duplicate(self):
        url1 = "https://github.com/example/old.git"
        url2 = "https://github.com/example/new.git"
        backend.set_git_remote(self.d, url1, "origin")

        # Update remote safely using set_git_remote
        ok, msg = backend.set_git_remote(self.d, url2, "origin")
        self.assertTrue(ok, msg)
        self.assertIn("updated", msg.lower())

        ok2, _, remotes = backend.get_git_remotes(self.d)
        self.assertTrue(ok2)
        self.assertEqual(remotes.get("origin"), url2)

    def test_remote_persistence_in_project_json(self):
        test_url = "https://github.com/testuser/dsa.git"
        # Save repo config with remote
        ok, msg = backend.save_repository_config(self.d, test_url)
        self.assertTrue(ok, msg)

        config, _ = backend.load_config()
        self.assertIsNotNone(config)
        self.assertIn("git", config)
        self.assertEqual(config["git"].get("remote_url"), test_url)
        self.assertEqual(config["git"].get("remote_name"), "origin")


class TestVerifyGitConfiguration(unittest.TestCase):
    """Test the complete 8-step verification process (Part 7)."""
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        _rm(self.d)

    def test_non_git_verification(self):
        rep = backend.verify_git_configuration(self.d)
        self.assertFalse(rep["success"])
        self.assertIn("not inside a Git repository", rep["message"])

    def test_git_repo_no_remote_verification(self):
        _mk(self.d)
        rep = backend.verify_git_configuration(self.d)
        self.assertTrue(rep["success"])
        self.assertTrue(rep["is_repo"])
        self.assertEqual(rep["repo_root"].resolve(), self.d.resolve())
        self.assertIn("No Git remote configured", rep["message"])

    def test_git_repo_with_remote_verification(self):
        _mk(self.d)
        url = "https://github.com/user/my-dsa.git"
        rep = backend.verify_git_configuration(self.d, url)
        self.assertTrue(rep["success"])
        self.assertEqual(rep["remote_url"], url)
        self.assertIn("Remote: origin", rep["message"])
        self.assertIn(url, rep["message"])


class TestGetGitStatus(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        _mk(self.d)

    def tearDown(self):
        _rm(self.d)

    def test_clean(self):
        f = self.d / "a.py"
        f.write_text("x", encoding="utf-8")
        _sc(self.d, f)
        ok, _, s = backend.get_git_status(self.d)
        self.assertTrue(ok)
        self.assertEqual(s, "")

    def test_untracked(self):
        f = self.d / "u.py"
        f.write_text("x", encoding="utf-8")
        ok, _, s = backend.get_git_status(self.d)
        self.assertTrue(ok)
        self.assertIn("u.py", s)

    def test_staged(self):
        f = self.d / "s.py"
        f.write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "--", str(f)], cwd=str(self.d), capture_output=True)
        ok, _, s = backend.get_git_status(self.d)
        self.assertTrue(ok)
        self.assertIn("s.py", s)

    def test_triple(self):
        self.assertEqual(len(backend.get_git_status(self.d)), 3)


class TestGitAddFile(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        _mk(self.d)

    def tearDown(self):
        _rm(self.d)

    def test_valid(self):
        f = self.d / "sol.py"
        f.write_text("x", encoding="utf-8")
        ok, msg = backend.git_add_file(self.d, f)
        self.assertTrue(ok, msg)

    def test_traversal_blocked(self):
        out = Path(tempfile.mkdtemp())
        try:
            ef = out / "evil.py"
            ef.write_text("x", encoding="utf-8")
            ok, msg = backend.git_add_file(self.d, ef)
            self.assertFalse(ok)
            self.assertIn("outside", msg.lower())
        finally:
            _rm(out)

    def test_missing_file(self):
        ok, msg = backend.git_add_file(self.d, self.d / "ghost.py")
        self.assertFalse(ok)
        self.assertIn("not exist", msg.lower())

    def test_subdir_file(self):
        sd = self.d / "Arrays"
        sd.mkdir()
        f = sd / "TS.py"
        f.write_text("x", encoding="utf-8")
        ok, msg = backend.git_add_file(self.d, f)
        self.assertTrue(ok, msg)

    def test_tuple(self):
        f = self.d / "x.py"
        f.write_text("x", encoding="utf-8")
        self.assertEqual(len(backend.git_add_file(self.d, f)), 2)

    def test_git_operations_from_subdirectory_use_verified_root(self):
        """When repo_path is a subdirectory, git_add_file executes against the git root."""
        sd = self.d / "Arrays"
        sd.mkdir()
        f = sd / "Problem.cpp"
        f.write_text("int main(){}", encoding="utf-8")

        # Call with subdirectory as repo_path
        ok, msg = backend.git_add_file(sd, f)
        self.assertTrue(ok, msg)
        _, _, st = backend.get_git_status(self.d)
        self.assertTrue(st.strip().startswith("A"))


class TestGitCommit(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        _mk(self.d)

    def tearDown(self):
        _rm(self.d)

    def _stage(self, n="s.py"):
        f = self.d / n
        f.write_text("x", encoding="utf-8")
        backend.git_add_file(self.d, f)
        return f

    def test_commit(self):
        self._stage()
        ok, msg = backend.git_commit(self.d, "Add sol")
        self.assertTrue(ok, msg)
        self.assertIn("Commit successful", msg)

    def test_empty_msg(self):
        self._stage()
        ok, msg = backend.git_commit(self.d, "")
        self.assertFalse(ok)
        self.assertIn("required", msg.lower())

    def test_whitespace_msg(self):
        self._stage()
        ok, msg = backend.git_commit(self.d, "   ")
        self.assertFalse(ok)
        self.assertIn("required", msg.lower())

    def test_msg_in_log(self):
        self._stage()
        backend.git_commit(self.d, "Add TwoSum in Arrays")
        log = subprocess.run(["git", "log", "--oneline", "-1"],
                             cwd=str(self.d), capture_output=True, text=True)
        self.assertIn("TwoSum", log.stdout)

    def test_nothing_staged_fails(self):
        ok, _ = backend.git_commit(self.d, "nothing")
        self.assertFalse(ok)

    def test_tuple(self):
        self.assertEqual(len(backend.git_commit(self.d, "m")), 2)


class TestGitPush(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        _mk(self.d)

    def tearDown(self):
        _rm(self.d)

    def _ic(self):
        f = self.d / "s.py"
        f.write_text("x", encoding="utf-8")
        backend.git_add_file(self.d, f)
        backend.git_commit(self.d, "init")

    def test_no_remote(self):
        self._ic()
        ok, msg = backend.git_push(self.d)
        self.assertFalse(ok)
        self.assertIn("no Git remote is configured", msg)

    def test_bare_remote(self):
        bare = Path(tempfile.mkdtemp())
        try:
            subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", str(bare)],
                           cwd=str(self.d), check=True, capture_output=True)
            self._ic()
            br = subprocess.run(["git", "branch", "--show-current"],
                                cwd=str(self.d), capture_output=True, text=True)
            branch = br.stdout.strip() or "master"
            subprocess.run(["git", "push", "--set-upstream", "origin", branch],
                           cwd=str(self.d), capture_output=True)
            ok, msg = backend.git_push(self.d)
            self.assertTrue(ok, "Push failed: " + msg)
        finally:
            _rm(bare)

    def test_tuple(self):
        self.assertEqual(len(backend.git_push(self.d)), 2)


class TestCustomPlatforms(unittest.TestCase):
    """Test custom platforms save, persistence, duplicates, and file generation (Parts 13-19)."""
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        _rm(self.d)

    def test_builtin_platforms_exist(self):
        all_plats = backend.get_all_platforms()
        for b in ["LeetCode", "CodeChef", "HackerRank", "Codeforces", "GeeksForGeeks", "Other"]:
            self.assertIn(b, all_plats)

    def test_save_custom_platform_and_persistence(self):
        plat_name = "Smart Interview"
        ok, msg = backend.save_custom_platform(plat_name)
        self.assertTrue(ok, msg)

        # Check immediate listing
        custom_list = backend.get_custom_platforms()
        self.assertIn(plat_name, custom_list)

        all_plats = backend.get_all_platforms()
        self.assertIn(plat_name, all_plats)
        # Should be before 'Other'
        self.assertEqual(all_plats[-1], "Other")

        # Restart persistence: reload config directly from file
        cfg, _ = backend.load_config()
        self.assertIn(plat_name, cfg.get("platforms", {}).get("custom", []))

        # Cleanup
        backend.delete_custom_platform(plat_name)

    def test_duplicate_platform_rejected(self):
        plat = "InterviewBit"
        ok1, msg1 = backend.save_custom_platform(plat)
        self.assertTrue(ok1, msg1)

        # Duplicate with leading/trailing spaces
        ok2, msg2 = backend.save_custom_platform(f"  {plat}  ")
        self.assertFalse(ok2)
        self.assertIn("already saved", msg2)

        # Case-insensitive duplicate
        ok3, msg3 = backend.save_custom_platform(plat.lower())
        self.assertFalse(ok3)
        self.assertIn("already saved", msg3)

        # Built-in duplicate
        ok4, msg4 = backend.save_custom_platform("LeetCode")
        self.assertFalse(ok4)
        self.assertIn("built-in", msg4)

        # Cleanup
        backend.delete_custom_platform(plat)

    def test_empty_platform_rejected(self):
        ok1, _ = backend.save_custom_platform("")
        self.assertFalse(ok1)
        ok2, _ = backend.save_custom_platform("   ")
        self.assertFalse(ok2)

    def test_generated_source_file_contains_custom_platform_header(self):
        plat_name = "Smart Interview"
        backend.save_custom_platform(plat_name)

        ok, msg, fpath = backend.create_problem_file(
            title="Mean Median Mode",
            platform=plat_name,
            language="C++",
            category="Arrays",
            description="Find mean, median and mode",
            solution_code="int main(){}",
            repo_path=self.d,
        )
        self.assertTrue(ok, msg)
        self.assertTrue(fpath.is_file())

        content = fpath.read_text(encoding="utf-8")
        self.assertIn(f"Platform: {plat_name}", content)
        self.assertNotIn("Platform: Other", content)

        # Platform does not create folders (Part 19)
        self.assertTrue((self.d / "Arrays" / fpath.name).exists())
        self.assertFalse((self.d / plat_name).exists())

        # Cleanup
        backend.delete_custom_platform(plat_name)


class TestPhase2EndToEnd(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        _mk(self.d)
        cat = self.d / "Arrays"
        cat.mkdir()
        self.pf = cat / "TwoSum.py"
        self.pf.write_text("# TwoSum solution", encoding="utf-8")

    def tearDown(self):
        _rm(self.d)

    def test_full_workflow(self):
        ok, _ = backend.is_git_available()
        self.assertTrue(ok)
        ok, _ = backend.is_git_repository(self.d)
        self.assertTrue(ok)
        ok, _, s = backend.get_git_status(self.d)
        self.assertTrue(ok)
        self.assertTrue("TwoSum.py" in s or "Arrays" in s, "Status: " + s)
        ok, msg = backend.git_add_file(self.d, self.pf)
        self.assertTrue(ok, msg)
        ok, _, s = backend.get_git_status(self.d)
        self.assertTrue("TwoSum.py" in s or "Arrays" in s, "Status: " + s)
        self.assertTrue(s.strip().startswith("A"), "Expected staged A prefix: " + s)
        ok, msg = backend.git_commit(self.d, "Add TwoSum - Arrays")
        self.assertTrue(ok, msg)
        self.assertIn("Commit successful", msg)
        ok, _, s = backend.get_git_status(self.d)
        self.assertTrue(ok)
        self.assertEqual(s, "")

    def test_traversal_blocked(self):
        out = Path(tempfile.mkdtemp())
        try:
            e = out / "evil.cpp"
            e.write_text("x", encoding="utf-8")
            ok, msg = backend.git_add_file(self.d, e)
            self.assertFalse(ok)
            self.assertIn("outside", msg.lower())
        finally:
            _rm(out)

    def test_no_commit_without_stage(self):
        ok, _ = backend.git_commit(self.d, "nothing staged")
        self.assertFalse(ok)

    def test_only_target_staged(self):
        other = self.d / "other.py"
        other.write_text("x", encoding="utf-8")
        backend.git_add_file(self.d, self.pf)
        _, _, s = backend.get_git_status(self.d)
        staged = [ln for ln in s.splitlines() if ln.startswith("A")]
        self.assertFalse(any("other" in ln for ln in staged),
                         "other.py must NOT be staged")


if __name__ == "__main__":
    unittest.main(verbosity=2)