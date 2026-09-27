"""
test_metadata.py - Automated test suite for the Complete Metadata Model (Tags, Importance, Multi-language header verification).

Tests:
1. C++ metadata generation with all fields.
2. Java metadata generation with all fields.
3. Python metadata generation with all fields.
4. Platform persistence in header.
5. Primary Category persistence in header.
6. Concepts / Techniques persistence in header.
7. Data Structures persistence in header.
8. Tags persistence in header.
9. Built-in tag suggestions.
10. Custom tag creation.
11. Custom tag persistence in project.json.
12. Duplicate tag prevention (case-insensitive against built-in and saved tags).
13. Importance persistence (numeric 1-5).
14. Time Complexity persistence.
15. Space Complexity persistence.
16. Added Date persistence.
17. Problem Description persistence.
18. Solution code remains unchanged and exact.
19. Primary Category still determines physical folder.
20. Tags do not determine physical folder.
21. Custom tag deletion safety.
"""

import json
from pathlib import Path
import shutil
import tempfile
import pytest

from engine import backend


@pytest.fixture
def isolated_env():
    """Create an isolated temporary environment with a mocked project.json and temp repo."""
    temp_dir = Path(tempfile.mkdtemp()).resolve()
    temp_config = temp_dir / "project.json"
    temp_repo = temp_dir / "DSA"
    temp_repo.mkdir(parents=True, exist_ok=True)

    initial_config = {
        "repository": str(temp_repo),
        "repository_path": str(temp_repo),
        "default_language": "cpp",
        "platforms": {"custom": ["Smart Interview"]},
        "categories": {"custom": ["Math"]},
        "tags": {"custom": []},
        "git": {"remote_name": "origin", "remote_url": ""},
    }
    with open(temp_config, "w", encoding="utf-8") as f:
        json.dump(initial_config, f, indent=4)

    orig_get_config_path = backend.get_config_path
    backend.get_config_path = lambda: temp_config

    yield {
        "temp_dir": temp_dir,
        "config_path": temp_config,
        "repo_path": temp_repo,
    }

    backend.get_config_path = orig_get_config_path
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# TAG SYSTEM TESTS
# ==============================================================================

def test_builtin_tags():
    """Verify built-in tags are present and in standard format."""
    all_tags = backend.get_all_tags()
    for b in backend.BUILTIN_TAGS:
        assert b in all_tags
    assert "Interview" in all_tags
    assert "Important" in all_tags
    assert "Revision" in all_tags
    assert "Tricky" in all_tags
    assert "Must-Do" in all_tags
    assert "Pattern" in all_tags


def test_custom_tag_creation_and_persistence(isolated_env):
    """Verify custom tag creation, immediate availability, and persistence in project.json."""
    ok, msg = backend.save_custom_tag("FAANG")
    assert ok is True
    assert "saved successfully" in msg.lower()

    # Appears immediately in get_all_tags
    all_tags = backend.get_all_tags()
    assert "FAANG" in all_tags

    # Persists in project.json
    custom_saved = backend.get_custom_tags()
    assert "FAANG" in custom_saved

    with open(isolated_env["config_path"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "FAANG" in data["tags"]["custom"]


def test_duplicate_tag_rejected(isolated_env):
    """Verify case-insensitive duplicate tag rejection."""
    backend.save_custom_tag("Google")

    # Duplicate of custom
    ok1, msg1 = backend.save_custom_tag("google")
    assert ok1 is False
    assert "already saved" in msg1.lower()

    ok2, msg2 = backend.save_custom_tag("  GOOGLE  ")
    assert ok2 is False
    assert "already saved" in msg2.lower()

    # Duplicate of built-in
    ok3, msg3 = backend.save_custom_tag("interview")
    assert ok3 is False
    assert "already a built-in tag" in msg3.lower()


def test_empty_tag_rejected(isolated_env):
    """Verify empty or whitespace-only tags are rejected."""
    ok1, msg1 = backend.save_custom_tag("")
    assert ok1 is False
    assert "cannot be empty" in msg1.lower()

    ok2, msg2 = backend.save_custom_tag("   ")
    assert ok2 is False
    assert "cannot be empty" in msg2.lower()


def test_delete_custom_tag(isolated_env):
    """Verify custom tags can be deleted and built-in tags cannot be deleted."""
    backend.save_custom_tag("TempTag")
    assert "TempTag" in backend.get_custom_tags()

    ok, msg = backend.delete_custom_tag("TempTag")
    assert ok is True
    assert "TempTag" not in backend.get_custom_tags()

    # Try deleting built-in tag
    ok_builtin, msg_builtin = backend.delete_custom_tag("Interview")
    assert ok_builtin is False
    assert "cannot delete built-in tag" in msg_builtin.lower()


# ==============================================================================
# COMPLETE METADATA HEADER GENERATION TESTS (C++, Java, Python)
# ==============================================================================

def test_cpp_metadata_generation(isolated_env):
    """Verify C++ file metadata generation with all fields."""
    repo = isolated_env["repo_path"]
    code = "int findMissing(vector<int>& a) { return 0; }"

    ok, msg, file_path = backend.create_problem_file(
        title="The Missing Number",
        platform="Smart Interview",
        language="C++",
        category="Math",
        description="Given an array containing n distinct numbers in range [0, n], return missing number.",
        solution_code=code,
        repo_path=repo,
        concepts="Hashing, Two Pointer",
        data_structures="Array, HashSet",
        tags="Interview, Revision, Tricky",
        importance="5 - ★★★★★ (Critical / Must-Do)",
        time_complexity="O(n)",
        space_complexity="O(1)",
    )
    assert ok is True
    assert file_path.exists()
    assert file_path.parent == repo / "Math"

    content = file_path.read_text(encoding="utf-8")

    # Header structure check
    assert "/*" in content
    assert "Problem: The Missing Number" in content
    assert "Platform: Smart Interview" in content
    assert "Language: C++" in content
    assert "Primary Category: Math" in content
    assert "Concepts / Techniques: Hashing, Two Pointer" in content
    assert "Data Structures: Array, HashSet" in content
    assert "Tags: Interview, Revision, Tricky" in content
    assert "Importance: 5" in content
    assert "Time Complexity: O(n)" in content
    assert "Space Complexity: O(1)" in content
    assert "Added:" in content
    assert "Problem Description:" in content
    assert "Given an array containing n distinct numbers in range [0, n], return missing number." in content
    assert "*/" in content

    # Solution code intact
    assert content.endswith(code)


def test_java_metadata_generation(isolated_env):
    """Verify Java file metadata generation with all fields."""
    repo = isolated_env["repo_path"]
    code = "class Solution { public int solve() { return 1; } }"

    ok, msg, file_path = backend.create_problem_file(
        title="Java Problem",
        platform="LeetCode",
        language="Java",
        category="Arrays",
        description="Java solution description.",
        solution_code=code,
        repo_path=repo,
        concepts="Binary Search",
        data_structures="Array",
        tags="Must-Do, Important",
        importance="4",
        time_complexity="O(log n)",
        space_complexity="O(1)",
    )
    assert ok is True
    assert file_path.exists()

    content = file_path.read_text(encoding="utf-8")
    assert "/*" in content
    assert "Problem: Java Problem" in content
    assert "Platform: LeetCode" in content
    assert "Language: Java" in content
    assert "Primary Category: Arrays" in content
    assert "Concepts / Techniques: Binary Search" in content
    assert "Data Structures: Array" in content
    assert "Tags: Must-Do, Important" in content
    assert "Importance: 4" in content
    assert "Time Complexity: O(log n)" in content
    assert "Space Complexity: O(1)" in content
    assert content.endswith(code)


def test_python_metadata_generation(isolated_env):
    """Verify Python file metadata generation with docstring header."""
    repo = isolated_env["repo_path"]
    code = "def solve(nums):\n    return sum(nums)"

    ok, msg, file_path = backend.create_problem_file(
        title="Python Problem",
        platform="Codeforces",
        language="Python",
        category="Recursion",
        description="Python recursion problem.",
        solution_code=code,
        repo_path=repo,
        concepts="Backtracking",
        data_structures="Stack",
        tags="Pattern, Tricky",
        importance="2",
        time_complexity="O(2^n)",
        space_complexity="O(n)",
    )
    assert ok is True
    assert file_path.exists()

    content = file_path.read_text(encoding="utf-8")
    assert '"""' in content
    assert "Problem: Python Problem" in content
    assert "Platform: Codeforces" in content
    assert "Language: Python" in content
    assert "Primary Category: Recursion" in content
    assert "Concepts / Techniques: Backtracking" in content
    assert "Data Structures: Stack" in content
    assert "Tags: Pattern, Tricky" in content
    assert "Importance: 2" in content
    assert "Time Complexity: O(2^n)" in content
    assert "Space Complexity: O(n)" in content
    assert content.endswith(code)


def test_tags_do_not_determine_physical_folder(isolated_env):
    """Tags must never determine physical folder placement."""
    repo = isolated_env["repo_path"]

    ok, msg, file_path = backend.create_problem_file(
        title="Tag Placement Problem",
        platform="LeetCode",
        language="C++",
        category="Math",
        description="Desc",
        solution_code="int solve() {}",
        repo_path=repo,
        tags="Hashing, Trees, Graphs",
        importance="5",
    )
    assert ok is True
    # Physical directory MUST be Math, NOT Hashing, Trees, or Graphs!
    assert file_path.parent == repo / "Math"
    assert not (repo / "Hashing").exists()
    assert not (repo / "Trees").exists()
    assert not (repo / "Graphs").exists()


def test_empty_optional_metadata(isolated_env):
    """Empty optional metadata fields should be handled gracefully without crashing."""
    repo = isolated_env["repo_path"]
    code = "int solve() {}"

    ok, msg, file_path = backend.create_problem_file(
        title="Minimal Problem",
        platform="LeetCode",
        language="C++",
        category="Uncategorized",
        description="Desc",
        solution_code=code,
        repo_path=repo,
        concepts=None,
        data_structures=None,
        tags=None,
        importance=None,
    )
    assert ok is True
    content = file_path.read_text(encoding="utf-8")
    assert "Problem: Minimal Problem" in content
    assert "Primary Category: Uncategorized" in content
    assert "Tags: \n" in content or "Tags:\n" in content
    assert "Importance: 3" in content  # Default fallback
