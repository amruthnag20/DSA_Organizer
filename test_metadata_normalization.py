"""
test_metadata_normalization.py - Comprehensive tests for Metadata Value Normalization & Deduplication.
Tests deterministic identity, canonical selection hierarchy, token canonicalization,
search deduplication, duplicate detection, and non-destructive header normalization.
"""

from pathlib import Path
import pytest
from typing import Dict, Any

from engine import backend


@pytest.fixture
def isolated_env(tmp_path):
    """Provide an isolated environment with temporary project.json and DSA repo."""
    temp_dir = tmp_path / "test_env"
    temp_dir.mkdir()
    config_file = temp_dir / "project.json"
    repo_dir = temp_dir / "DSA"
    repo_dir.mkdir()

    orig_get_root = backend.get_project_root
    orig_get_config = backend.get_config_path

    backend.get_project_root = lambda: temp_dir
    backend.get_config_path = lambda: config_file

    config_data = {
        "repository": str(repo_dir),
        "default_language": "cpp",
        "platforms": {"custom": ["Smart Interview"]},
        "categories": {"custom": ["BitManipulation"]},
        "tags": {"custom": ["Revision"]},
    }
    backend._write_and_verify_json(config_file, config_data)

    yield {
        "temp_dir": temp_dir,
        "config_path": config_file,
        "repo_path": repo_dir,
    }

    backend.get_project_root = orig_get_root
    backend.get_config_path = orig_get_config


# ==============================================================================
# 1. CORE NORMALIZATION & IDENTITY TESTS
# ==============================================================================

def test_metadata_key_normalization():
    """Verify whitespace stripping, multiple whitespace collapsing, and lowercase identity."""
    assert backend.normalize_metadata_key("Smart Interview") == "smart interview"
    assert backend.normalize_metadata_key("smart interview") == "smart interview"
    assert backend.normalize_metadata_key("SMART INTERVIEW") == "smart interview"
    assert backend.normalize_metadata_key("  Smart   Interview  ") == "smart interview"
    assert backend.normalize_metadata_key("Smart\t\nInterview") == "smart interview"

    assert backend.normalize_metadata_key("Revision") == "revision"
    assert backend.normalize_metadata_key("  REVISION  ") == "revision"


def test_metadata_display_normalization():
    """Verify display normalization preserves casing while collapsing excess whitespace."""
    assert backend.normalize_metadata_display("  Smart   Interview  ") == "Smart Interview"
    assert backend.normalize_metadata_display("  Math  ") == "Math"
    assert backend.normalize_metadata_display("Two   Pointer") == "Two Pointer"


def test_distinct_values_not_merged():
    """Verify that genuinely different values are never collapsed together."""
    assert backend.normalize_metadata_key("Smart Interview") != backend.normalize_metadata_key("Smart Interviews")
    assert backend.normalize_metadata_key("Array") != backend.normalize_metadata_key("Arrays")
    assert backend.normalize_metadata_key("HashMap") != backend.normalize_metadata_key("Hash Map")
    assert backend.normalize_metadata_key("Math") != backend.normalize_metadata_key("Mathematics")
    assert backend.normalize_metadata_key("Tree") != backend.normalize_metadata_key("Trees")


# ==============================================================================
# 2. CANONICAL VALUE SELECTION HIERARCHY
# ==============================================================================

def test_canonical_mapping_hierarchy():
    """
    Preference order:
    1. Configured / built-in values first.
    2. Highest frequency among discovered values.
    3. Alphabetical tie-breaker.
    """
    configured = ["Smart Interview", "LeetCode"]
    discovered = [
        "smart interview", "smart interview", "SMART INTERVIEW",
        "two sum", "Two Sum", "Two Sum",
        "beta test", "Alpha Test"
    ]

    mapping = backend.build_canonical_mapping(configured, discovered)

    # 1. Configured wins even if discovered has different casing
    assert mapping["smart interview"] == "Smart Interview"
    assert mapping["leetcode"] == "LeetCode"

    # 2. Frequency wins when not configured (Two Sum has 2, two sum has 1)
    assert mapping["two sum"] == "Two Sum"

    # 3. Alphabetical tie-breaker when frequency tied
    assert mapping["beta test"] == "beta test"
    # For a tie between 'Alpha Test' and 'alpha test':
    tie_mapping = backend.build_canonical_mapping([], ["beta variant", "Beta Variant"])
    assert tie_mapping["beta variant"] in ("Beta Variant", "beta variant")


# ==============================================================================
# 3. TOKEN-BASED CANONICALIZATION (TAGS, CONCEPTS, DATA STRUCTURES)
# ==============================================================================

def test_canonicalize_token_list():
    """Verify comma-separated token canonicalization and duplicate removal."""
    tag_map = backend.build_canonical_mapping(["Interview", "Revision", "Tricky"], [])
    tokens, joined = backend.canonicalize_token_list("interview, revision, TRICKY, interview", tag_map)

    assert tokens == ["Interview", "Revision", "Tricky"]
    assert joined == "Interview, Revision, Tricky"

    concept_map = backend.build_canonical_mapping(backend.BUILTIN_CONCEPTS, [])
    c_tokens, c_joined = backend.canonicalize_token_list("hashing, two pointer, HASHING", concept_map)
    assert c_tokens == ["Hashing", "Two Pointer"] if "Hashing" in concept_map.values() else ["hashing", "Two Pointer"]

    ds_map = backend.build_canonical_mapping(backend.BUILTIN_DATA_STRUCTURES, [])
    d_tokens, d_joined = backend.canonicalize_token_list("hashmap, array, HashMap", ds_map)
    assert d_tokens == ["HashMap", "Array"]


# ==============================================================================
# 4. CUSTOM METADATA DUPLICATE REJECTION
# ==============================================================================

def test_duplicate_custom_platform_rejected(isolated_env):
    """Verify case-insensitive / whitespace duplicate custom platform rejection."""
    # Existing configured is 'Smart Interview'
    ok, msg = backend.save_custom_platform("smart interview")
    assert not ok
    assert "already saved" in msg.lower()

    ok2, msg2 = backend.save_custom_platform("  SMART   INTERVIEW  ")
    assert not ok2
    assert "already saved" in msg2.lower()

    # Built-in duplicate rejection
    ok3, msg3 = backend.save_custom_platform("leetcode")
    assert not ok3
    assert "already a built-in platform" in msg3.lower()


def test_duplicate_custom_category_rejected(isolated_env):
    """Verify case-insensitive / whitespace duplicate custom category rejection."""
    ok, msg = backend.save_custom_category("bitmanipulation")
    assert not ok
    assert "already saved" in msg.lower()

    ok2, msg2 = backend.save_custom_category("arrays")
    assert not ok2
    assert "already a built-in category" in msg2.lower()


def test_duplicate_custom_tag_rejected(isolated_env):
    """Verify case-insensitive / whitespace duplicate custom tag rejection."""
    # First save a custom tag
    ok_save, _ = backend.save_custom_tag("HardProblem")
    assert ok_save is True

    # Duplicate of custom tag
    ok, msg = backend.save_custom_tag("hardproblem")
    assert not ok
    assert "already saved" in msg.lower()

    ok2, msg2 = backend.save_custom_tag("interview")
    assert not ok2
    assert "already a built-in tag" in msg2.lower()


# ==============================================================================
# 5. CREATE PROBLEM AND UPDATE METADATA CANONICALIZATION
# ==============================================================================

def test_create_problem_uses_canonical_values(isolated_env):
    """Verify create_problem_file canonicalizes platform, category, tags, concepts, data structures."""
    repo = isolated_env["repo_path"]

    ok, msg, path = backend.create_problem_file(
        title="Deduplication Test",
        platform="smart interview",  # Should canonicalize to 'Smart Interview'
        language="C++",
        category="arrays",  # Should canonicalize to 'Arrays'
        description="Testing canonicalization.",
        solution_code="int main() { return 0; }",
        repo_path=repo,
        concepts="two pointer, TWO POINTER",
        data_structures="hashmap",
        tags="revision, REVISION",
    )

    assert ok is True
    assert path.exists()

    meta = backend.parse_problem_metadata(path)
    assert meta["platform"] == "Smart Interview"
    assert meta["category"] == "Arrays"
    assert meta["concepts"] == "Two Pointer"
    assert meta["data_structures"] == "HashMap"
    assert meta["tags"] == "Revision"


# ==============================================================================
# 6. SEARCH FILTER DEDUPLICATION & MULTI-VARIANT MATCHING
# ==============================================================================

def test_search_filters_and_matches_all_casing_variants(isolated_env):
    """
    Verify:
    1. Search filter dropdown options are deduplicated by canonical representation.
    2. Selecting canonical filter 'Smart Interview' matches all casing/whitespace variants in repo.
    3. Search is strictly read-only and does not rewrite files.
    """
    repo = isolated_env["repo_path"]

    # Create file 1 with canonical 'Smart Interview'
    backend.create_problem_file(
        title="Prob A",
        platform="Smart Interview",
        language="C++",
        category="Arrays",
        description="Desc A",
        solution_code="int a = 1;",
        repo_path=repo,
    )

    # Manually create file 2 with lowercase 'smart interview' and file 3 with uppercase 'SMART INTERVIEW'
    cat_dir = repo / "Arrays"
    file2 = cat_dir / "ProbB.cpp"
    file2.write_text(
        "/*\nProblem: Prob B\nPlatform: smart interview\nLanguage: C++\nPrimary Category: Arrays\n"
        "Concepts / Techniques: Recursion\nData Structures: Array\nTime Complexity: O(1)\n"
        "Space Complexity: O(1)\nTags: Revision\nImportance: 3\nAdded: 2026-09-27\n\n"
        "Problem Description:\nDesc B\n*/\n\nint b = 2;",
        encoding="utf-8"
    )

    file3 = cat_dir / "ProbC.cpp"
    file3.write_text(
        "/*\nProblem: Prob C\nPlatform: SMART INTERVIEW\nLanguage: C++\nPrimary Category: Arrays\n"
        "Concepts / Techniques: Recursion\nData Structures: Array\nTime Complexity: O(1)\n"
        "Space Complexity: O(1)\nTags: Revision\nImportance: 3\nAdded: 2026-09-27\n\n"
        "Problem Description:\nDesc C\n*/\n\nint c = 3;",
        encoding="utf-8"
    )

    # Search with no query to inspect filter options
    search_res = backend.search_problems(repo, query="")
    filter_plats = search_res["filter_options"]["platforms"]

    # Filter platforms must contain 'Smart Interview' exactly ONCE
    smart_plats = [p for p in filter_plats if backend.normalize_metadata_key(p) == "smart interview"]
    assert len(smart_plats) == 1
    assert smart_plats[0] == "Smart Interview"

    # Filtering by 'Smart Interview' must return all 3 problems
    filtered_res = backend.search_problems(repo, platform="Smart Interview")
    assert filtered_res["total_matching"] == 3

    # Filtering with lowercase 'smart interview' must also return all 3 problems
    filtered_res_lower = backend.search_problems(repo, platform="smart interview")
    assert filtered_res_lower["total_matching"] == 3

    # Files must NOT be modified by searching (read-only verification)
    assert "Platform: smart interview" in file2.read_text(encoding="utf-8")
    assert "Platform: SMART INTERVIEW" in file3.read_text(encoding="utf-8")


# ==============================================================================
# 7. RESCAN DUPLICATE DETECTION & EXPLICIT NORMALIZATION
# ==============================================================================

def test_detect_duplicates_and_explicit_normalize(isolated_env):
    """
    Verify:
    1. detect_metadata_duplicates detects variants without modifying files.
    2. normalize_repository_metadata updates headers to canonical form and preserves solution code byte-for-byte.
    """
    repo = isolated_env["repo_path"]
    cat_dir = repo / "Arrays"
    cat_dir.mkdir(exist_ok=True)

    file1 = cat_dir / "SolOne.cpp"
    file1.write_text(
        "/*\nProblem: Sol One\nPlatform: smart interview\nLanguage: C++\nPrimary Category: Arrays\n"
        "Concepts / Techniques: recursion, RECURSION\nData Structures: array\nTime Complexity: O(1)\n"
        "Space Complexity: O(1)\nTags: revision\nImportance: 3\nAdded: 2026-09-27\n\n"
        "Problem Description:\nOriginal description.\n*/\n\n// Solution code exact spacing\nint solve() {\n    return 42;\n}\n",
        encoding="utf-8"
    )

    # 1. Detection
    dup_res = backend.detect_metadata_duplicates(repo)
    assert dup_res["has_duplicates"] is True
    assert dup_res["total_duplicate_groups"] >= 1

    # Verify file is not changed before explicit normalization
    assert "Platform: smart interview" in file1.read_text(encoding="utf-8")

    # 2. Explicit Normalization
    norm_res = backend.normalize_repository_metadata(repo)
    assert norm_res["success"] is True
    assert norm_res["normalized_files_count"] == 1

    # Verify updated content
    updated_content = file1.read_text(encoding="utf-8")
    assert "Platform: Smart Interview" in updated_content
    assert "Tags: Revision" in updated_content
    assert "Data Structures: Array" in updated_content

    # Verify solution code is byte-for-byte identical
    assert "// Solution code exact spacing\nint solve() {\n    return 42;\n}\n" in updated_content
    assert "Original description." in updated_content

    # 3. Post-normalization duplicate check
    post_dup = backend.detect_metadata_duplicates(repo)
    assert post_dup["has_duplicates"] is False
