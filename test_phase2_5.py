"""
test_phase2_5.py - Comprehensive automated test suite for Phase 2.5 requirements.

Covers:
- Part 31:
  Git:
    1. Git executable detection.
    2. Git repository detection.
    3. Correct Git repository root detection.
    4. Configured path inside a Git repository.
    5. Remote detection.
    6. Remote persistence.
    7. Remote update.
    8. No-remote handling.
    9. Stage only intended file.
    10. Commit & staged verification.
    11. Push to a temporary local bare repository.
    12. No duplicate Git operations.
    13. Correct error handling.
  Custom Platforms:
    14. Built-in platforms still work.
    15. Add custom platform.
    16. Save custom platform.
    17. Custom platform appears immediately.
    18. Custom platform persists after restart.
    19. Duplicate platform rejected.
    20. Empty platform rejected.
    21. Source header contains the selected custom platform.
  Categories:
    22. Built-in categories still work.
    23. Add custom category.
    24. Save custom category.
    25. Custom category appears immediately.
    26. Custom category persists after restart.
    27. Duplicate category rejected.
    28. Empty category rejected.
    29. Path traversal category rejected.
    30. Math creates DSA/Math/, not DSA/Uncategorized/Math/.
    31. Multiple Math problems share the Math folder.
    32. Uncategorized still works.
    33. Existing files are not moved.
    34. Concepts such as Hashing do not change physical category placement.
    35. Git can stage/commit/push a problem inside a custom category.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Generator
import pytest

from engine import backend


@pytest.fixture
def isolated_env():
    """Create an isolated temporary environment with a mocked project.json and temp git repo."""
    temp_dir = Path(tempfile.mkdtemp()).resolve()
    temp_config = temp_dir / "project.json"
    temp_repo = temp_dir / "DSA"
    temp_repo.mkdir(parents=True, exist_ok=True)

    # Initialize git repo in temp_repo
    subprocess.run(["git", "init"], cwd=str(temp_repo), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "TestUser"], cwd=str(temp_repo), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(temp_repo), capture_output=True, check=True)

    initial_config = {
        "repository": str(temp_repo),
        "repository_path": str(temp_repo),
        "default_language": "cpp",
        "platforms": {"custom": []},
        "categories": {"custom": []},
        "git": {"remote_name": "origin", "remote_url": ""},
    }
    with open(temp_config, "w", encoding="utf-8") as f:
        json.dump(initial_config, f, indent=4)

    # Backup real config path and point to temp
    orig_get_config_path = backend.get_config_path
    backend.get_config_path = lambda: temp_config

    yield {
        "temp_dir": temp_dir,
        "config_path": temp_config,
        "repo_path": temp_repo,
    }

    # Restore
    backend.get_config_path = orig_get_config_path
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# GIT TESTS (1 to 13)
# ==============================================================================

def test_1_git_executable_detection():
    """1. Git executable detection."""
    is_avail, msg = backend.is_git_available()
    assert is_avail is True
    assert "git version" in msg.lower()


def test_2_git_repository_detection(isolated_env):
    """2. Git repository detection."""
    repo = isolated_env["repo_path"]
    is_repo, msg = backend.is_git_repository(repo)
    assert is_repo is True
    assert "detected" in msg.lower() or "found" in msg.lower()


def test_3_correct_git_repository_root_detection(isolated_env):
    """3. Correct Git repository root detection."""
    repo = isolated_env["repo_path"]
    is_repo, msg, root = backend.get_git_repo_root(repo)
    assert is_repo is True
    assert root.resolve() == repo.resolve()


def test_4_configured_path_inside_git_repository(isolated_env):
    """4. Configured path inside a Git repository (subdirectory)."""
    repo = isolated_env["repo_path"]
    sub_dir = repo / "Problems" / "SubFolder"
    sub_dir.mkdir(parents=True, exist_ok=True)

    is_repo, msg, root = backend.get_git_repo_root(sub_dir)
    assert is_repo is True
    assert root.resolve() == repo.resolve()


def test_5_remote_detection(isolated_env):
    """5. Remote detection."""
    repo = isolated_env["repo_path"]
    # Add a dummy remote
    dummy_url = "https://github.com/example/test_dsa.git"
    backend.set_git_remote(repo, dummy_url, "origin")

    ok, msg, remotes = backend.get_git_remotes(repo)
    assert ok is True
    assert "origin" in remotes
    assert remotes["origin"] == dummy_url


def test_6_remote_persistence(isolated_env):
    """6. Remote persistence in project.json."""
    repo = isolated_env["repo_path"]
    remote_url = "https://github.com/example/persisted_dsa.git"
    ok, msg = backend.save_repository_config(repo, remote_url)
    assert ok is True

    # Read back project.json directly
    config_path = isolated_env["config_path"]
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["git"]["remote_url"] == remote_url


def test_7_remote_update(isolated_env):
    """7. Remote update without error."""
    repo = isolated_env["repo_path"]
    url1 = "https://github.com/example/repo1.git"
    url2 = "https://github.com/example/repo2.git"

    ok, _ = backend.set_git_remote(repo, url1, "origin")
    assert ok is True

    ok2, msg2 = backend.set_git_remote(repo, url2, "origin")
    assert ok2 is True
    assert "updated" in msg2.lower()

    _, _, remotes = backend.get_git_remotes(repo)
    assert remotes["origin"] == url2


def test_8_no_remote_handling(isolated_env):
    """8. No-remote handling."""
    repo = isolated_env["repo_path"]
    ok, msg, remotes = backend.get_git_remotes(repo)
    assert ok is True
    assert remotes == {}
    assert "No Git remote configured" in msg


def test_9_stage_only_intended_file(isolated_env):
    """9. Stage only intended file."""
    repo = isolated_env["repo_path"]
    file1 = repo / "file1.cpp"
    file2 = repo / "file2.cpp"
    file1.write_text("int a = 1;", encoding="utf-8")
    file2.write_text("int b = 2;", encoding="utf-8")

    ok, msg = backend.git_add_file(repo, file1)
    assert ok is True

    # Check status
    ok, _, status = backend.get_git_status(repo)
    assert ok is True
    # file1 should be staged (A ), file2 should be untracked (??)
    lines = [l.strip() for l in status.splitlines()]
    file1_staged = any(l.startswith("A") and "file1.cpp" in l for l in lines)
    file2_untracked = any(l.startswith("??") and "file2.cpp" in l for l in lines)
    assert file1_staged is True
    assert file2_untracked is True


def test_10_commit_and_staged_verification(isolated_env):
    """10. Commit with staged verification (reject when nothing staged)."""
    repo = isolated_env["repo_path"]

    # Before staging anything, commit must fail with "Nothing staged to commit."
    ok, msg = backend.git_commit(repo, "Initial commit attempt")
    assert ok is False
    assert "nothing staged to commit" in msg.lower()

    # Now stage a file and commit
    f = repo / "solution.cpp"
    f.write_text("int main() {}", encoding="utf-8")
    backend.git_add_file(repo, f)

    ok, msg = backend.git_commit(repo, "Add solution")
    assert ok is True
    assert "commit successful" in msg.lower()

    # Immediately committing again with nothing staged must fail
    ok2, msg2 = backend.git_commit(repo, "Duplicate commit")
    assert ok2 is False
    assert "nothing staged to commit" in msg2.lower()


def test_11_push_to_local_bare_repo(isolated_env):
    """11. Push to a temporary local bare repository."""
    repo = isolated_env["repo_path"]
    bare_dir = isolated_env["temp_dir"] / "bare_remote.git"
    subprocess.run(["git", "init", "--bare", str(bare_dir)], capture_output=True, check=True)

    # Set remote to bare_dir
    backend.set_git_remote(repo, str(bare_dir), "origin")

    # Commit a file
    f = repo / "Main.cpp"
    f.write_text("// test", encoding="utf-8")
    backend.git_add_file(repo, f)
    backend.git_commit(repo, "Commit for push")

    # Rename master to main if needed to ensure branch is pushed
    subprocess.run(["git", "-C", str(repo), "branch", "-M", "main"], capture_output=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "main"], capture_output=True)

    # Now test backend.git_push
    # Create another commit
    f2 = repo / "Second.cpp"
    f2.write_text("// second", encoding="utf-8")
    backend.git_add_file(repo, f2)
    backend.git_commit(repo, "Second commit")

    push_ok, push_msg = backend.git_push(repo)
    assert push_ok is True
    assert "push successful" in push_msg.lower()


def test_12_no_duplicate_git_operations(isolated_env):
    """12. No duplicate Git operations."""
    repo = isolated_env["repo_path"]
    # Commit when clean
    ok1, msg1 = backend.git_commit(repo, "msg")
    assert ok1 is False
    assert "nothing staged to commit" in msg1.lower()


def test_13_correct_error_handling(isolated_env):
    """13. Correct error handling."""
    # Invalid directory
    non_existent = Path("C:/NonExistent_Dir_123456789")
    ok, msg, root = backend.get_git_repo_root(non_existent)
    assert ok is False
    assert root is None

    # Push without remote
    repo = isolated_env["repo_path"]
    push_ok, push_msg = backend.git_push(repo)
    assert push_ok is False
    assert "no git remote is configured" in push_msg.lower()


# ==============================================================================
# CUSTOM PLATFORMS TESTS (14 to 21)
# ==============================================================================

def test_14_builtin_platforms_still_work():
    """14. Built-in platforms still work."""
    platforms = backend.get_all_platforms()
    for b in backend.BUILTIN_PLATFORMS:
        assert b in platforms
    assert "Other" in platforms


def test_15_16_17_18_custom_platform_flow(isolated_env):
    """15, 16, 17, 18. Add, save, immediate appearance, and persistence of custom platform."""
    ok, msg = backend.save_custom_platform("Smart Interview")
    assert ok is True
    assert "saved successfully" in msg.lower()

    # Appears immediately in get_all_platforms()
    all_plats = backend.get_all_platforms()
    assert "Smart Interview" in all_plats

    # Persists in project.json
    custom_saved = backend.get_custom_platforms()
    assert "Smart Interview" in custom_saved

    with open(isolated_env["config_path"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "Smart Interview" in data["platforms"]["custom"]


def test_19_duplicate_platform_rejected(isolated_env):
    """19. Duplicate platform rejected case-insensitively."""
    backend.save_custom_platform("Smart Interview")

    # Variations
    ok1, msg1 = backend.save_custom_platform("smart interview")
    assert ok1 is False
    assert "already saved" in msg1.lower()

    ok2, msg2 = backend.save_custom_platform("  SMART INTERVIEW  ")
    assert ok2 is False
    assert "already saved" in msg2.lower()

    # Built-in duplicate
    ok3, msg3 = backend.save_custom_platform("leetcode")
    assert ok3 is False
    assert "already a built-in platform" in msg3.lower()


def test_20_empty_platform_rejected(isolated_env):
    """20. Empty platform rejected."""
    ok1, msg1 = backend.save_custom_platform("")
    assert ok1 is False
    assert "cannot be empty" in msg1.lower()

    ok2, msg2 = backend.save_custom_platform("    ")
    assert ok2 is False
    assert "cannot be empty" in msg2.lower()


def test_21_source_header_contains_custom_platform(isolated_env):
    """21. Source header contains the selected custom platform."""
    repo = isolated_env["repo_path"]
    backend.save_custom_platform("Smart Interview")

    ok, msg, file_path = backend.create_problem_file(
        title="Custom Plat Problem",
        platform="Smart Interview",
        language="C++",
        category="Arrays",
        description="Test desc",
        solution_code="int solve() { return 1; }",
        repo_path=repo,
    )
    assert ok is True
    content = file_path.read_text(encoding="utf-8")
    assert "Platform: Smart Interview" in content
    assert "Primary Category: Arrays" in content


# ==============================================================================
# CATEGORIES TESTS (22 to 35)
# ==============================================================================

def test_22_builtin_categories_still_work():
    """22. Built-in categories still work."""
    cats = backend.get_categories()
    for b in backend.DEFAULT_CATEGORIES:
        assert b in cats
    assert len(cats) >= len(backend.DEFAULT_CATEGORIES)


def test_23_24_25_26_custom_category_flow(isolated_env):
    """23, 24, 25, 26. Add, save, immediate appearance, and persistence of custom category."""
    ok, msg = backend.save_custom_category("Math")
    assert ok is True
    assert "saved successfully" in msg.lower()

    # Immediate appearance
    cats = backend.get_categories()
    assert "Math" in cats

    # Persistence
    saved_cats = backend.get_custom_categories()
    assert "Math" in saved_cats

    with open(isolated_env["config_path"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "Math" in data["categories"]["custom"]


def test_27_duplicate_category_rejected(isolated_env):
    """27. Duplicate category rejected case-insensitively."""
    backend.save_custom_category("Math")

    ok1, msg1 = backend.save_custom_category("math")
    assert ok1 is False
    assert "already saved" in msg1.lower()

    ok2, msg2 = backend.save_custom_category("  MATH  ")
    assert ok2 is False
    assert "already saved" in msg2.lower()

    # Built-in duplicate
    ok3, msg3 = backend.save_custom_category("arrays")
    assert ok3 is False
    assert "already a built-in category" in msg3.lower()


def test_28_empty_category_rejected(isolated_env):
    """28. Empty category rejected."""
    ok1, msg1 = backend.save_custom_category("")
    assert ok1 is False
    assert "cannot be empty" in msg1.lower()

    ok2, msg2 = backend.save_custom_category("   ")
    assert ok2 is False
    assert "cannot be empty" in msg2.lower()


def test_29_path_traversal_category_rejected(isolated_env):
    """29. Path traversal category rejected."""
    bad_cats = ["..", "../Math", r"..\Math", "C:\\Math", "C:/Math", "Math/Sub", "Math\\Sub"]
    for bad in bad_cats:
        ok, msg = backend.save_custom_category(bad)
        assert ok is False
        assert "unsafe" in msg.lower() or "invalid" in msg.lower() or "traversal" in msg.lower()


def test_30_math_creates_top_level_folder(isolated_env):
    """30. Math creates DSA/Math/, not DSA/Uncategorized/Math/."""
    repo = isolated_env["repo_path"]
    backend.save_custom_category("Math")

    ok, msg, file_path = backend.create_problem_file(
        title="The Missing Number",
        platform="LeetCode",
        language="C++",
        category="Math",
        description="Find missing",
        solution_code="int solve() {}",
        repo_path=repo,
    )
    assert ok is True
    assert file_path.exists()

    expected_dir = repo / "Math"
    assert file_path.parent == expected_dir
    assert expected_dir.is_dir()

    # Explicitly verify it is NOT inside Uncategorized
    uncategorized_dir = repo / "Uncategorized"
    assert not (uncategorized_dir / "Math").exists()


def test_31_multiple_math_problems_share_math_folder(isolated_env):
    """31. Multiple Math problems share the Math folder."""
    repo = isolated_env["repo_path"]
    backend.save_custom_category("Math")

    ok1, _, p1 = backend.create_problem_file(
        title="The Missing Number",
        platform="LeetCode",
        language="C++",
        category="Math",
        description="Desc 1",
        solution_code="int solve() {}",
        repo_path=repo,
    )
    ok2, _, p2 = backend.create_problem_file(
        title="Mean Median Mode",
        platform="LeetCode",
        language="C++",
        category="Math",
        description="Desc 2",
        solution_code="int solve() {}",
        repo_path=repo,
    )
    ok3, _, p3 = backend.create_problem_file(
        title="Prime Numbers",
        platform="LeetCode",
        language="C++",
        category="Math",
        description="Desc 3",
        solution_code="int solve() {}",
        repo_path=repo,
    )

    assert ok1 and ok2 and ok3
    math_dir = repo / "Math"
    assert p1.parent == math_dir
    assert p2.parent == math_dir
    assert p3.parent == math_dir

    # Only one Math folder exists
    assert (math_dir / "TheMissingNumber.cpp").exists()
    assert (math_dir / "MeanMedianMode.cpp").exists()
    assert (math_dir / "PrimeNumbers.cpp").exists()


def test_32_uncategorized_still_works(isolated_env):
    """32. Uncategorized still works as top-level category."""
    repo = isolated_env["repo_path"]
    ok, msg, file_path = backend.create_problem_file(
        title="Uncat Problem",
        platform="LeetCode",
        language="C++",
        category="Uncategorized",
        description="Desc",
        solution_code="int solve() {}",
        repo_path=repo,
    )
    assert ok is True
    assert file_path.parent == repo / "Uncategorized"
    assert file_path.exists()


def test_33_existing_files_are_not_moved(isolated_env):
    """33. Existing files are not moved when a new category is created."""
    repo = isolated_env["repo_path"]
    # Create problem in Uncategorized
    ok1, _, old_p = backend.create_problem_file(
        title="Old Problem",
        platform="LeetCode",
        language="C++",
        category="Uncategorized",
        description="Desc",
        solution_code="int solve() {}",
        repo_path=repo,
    )
    assert ok1 is True
    assert old_p.exists()

    # Now add Math category
    backend.save_custom_category("Math")

    # Old problem must remain in Uncategorized
    assert old_p.exists()
    assert old_p.parent == repo / "Uncategorized"


def test_34_concepts_do_not_change_physical_folder(isolated_env):
    """34. Concepts such as Hashing do not change physical category placement."""
    repo = isolated_env["repo_path"]
    backend.save_custom_category("Math")

    ok, _, file_path = backend.create_problem_file(
        title="Concept Test Problem",
        platform="Smart Interview",
        language="C++",
        category="Math",
        description="Desc",
        solution_code="int solve() {}",
        repo_path=repo,
        concepts="Hashing",
        data_structures="Array",
    )
    assert ok is True
    # Destination must be Math, NOT Hashing
    assert file_path.parent == repo / "Math"
    assert not (repo / "Hashing").exists()

    content = file_path.read_text(encoding="utf-8")
    assert "Primary Category: Math" in content
    assert "Concepts / Techniques: Hashing" in content


def test_35_git_stages_and_commits_custom_category_problem(isolated_env):
    """35. Git can stage/commit/push a problem inside a custom category."""
    repo = isolated_env["repo_path"]
    backend.save_custom_category("Math")

    ok, _, file_path = backend.create_problem_file(
        title="Git Math Problem",
        platform="LeetCode",
        language="C++",
        category="Math",
        description="Desc",
        solution_code="int solve() {}",
        repo_path=repo,
    )
    assert ok is True

    # Stage
    stage_ok, stage_msg = backend.git_add_file(repo, file_path)
    assert stage_ok is True

    # Status check
    _, _, status = backend.get_git_status(repo)
    assert "Math/GitMathProblem.cpp" in status

    # Commit
    commit_ok, commit_msg = backend.git_commit(repo, "Add Git Math Problem")
    assert commit_ok is True
    assert "commit successful" in commit_msg.lower()
