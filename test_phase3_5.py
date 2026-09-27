"""
test_phase3_5.py - Automated test suite for Phase 3.5: Repository Rescan & Metadata Repair.

Tests verify:
1. Basic scanning: empty repo, C++, Java, Python, multiple categories, ignore unrelated files, ignore .git.
2. Metadata parsing: complete headers, missing Tags, missing Importance, missing Data Structures,
   missing Concepts/Techniques, missing Complexity, missing Added date, malformed headers, no headers.
3. Metadata repair: preserving existing metadata, adding missing fields, byte-for-byte solution preservation,
   physical read-back verification, preserving file path without moving.
4. Categories & Folder consistency: folder match, category mismatch detection, mismatch file retention,
   Uncategorized support, custom top-level categories.
5. Tags & Importance: built-in tags, custom tags, duplicate prevention, 1-5 scale.
6. Repeatability & Idempotence: repeated scans without side-effects, rescan after repair transitioning from Incomplete to Complete.
"""

from datetime import date
import os
from pathlib import Path
import pytest
import shutil
import tempfile

from engine import backend


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository directory."""
    repo_dir = tmp_path / "TestDSA"
    repo_dir.mkdir()
    return repo_dir


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    """Isolate project.json configuration."""
    cfg_file = tmp_path / "project.json"
    monkeypatch.setattr(backend, "get_config_path", lambda: cfg_file)
    return cfg_file


# ==============================================================================
# 1. BASIC SCANNING TESTS
# ==============================================================================

def test_scan_empty_repository(temp_repo):
    """Scan empty repository returns 0 problems with success=True."""
    res = backend.scan_repository(temp_repo)
    assert res["success"] is True
    assert res["total_problems"] == 0
    assert res["complete_count"] == 0
    assert res["incomplete_count"] == 0
    assert res["problems"] == []


def test_scan_valid_cpp_file(temp_repo):
    """Scan repository with a complete C++ problem file."""
    cat_dir = temp_repo / "Arrays"
    cat_dir.mkdir()
    cpp_file = cat_dir / "TwoSum.cpp"
    
    content = backend.generate_problem_content(
        title="Two Sum",
        platform="LeetCode",
        language="C++",
        category="Arrays",
        description="Find two numbers that add up to target.",
        solution_code="class Solution {\npublic:\n    vector<int> twoSum() { return {}; }\n};\n",
        concepts="Two Pointer",
        data_structures="Array, HashMap",
        tags="Interview, Must-Do",
        importance="5",
        time_complexity="O(n)",
        space_complexity="O(n)",
    )
    cpp_file.write_text(content, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 1
    assert res["complete_count"] == 1
    assert res["incomplete_count"] == 0
    assert res["unreadable_count"] == 0
    assert res["mismatch_count"] == 0
    prob = res["problems"][0]
    assert prob["title"] == "Two Sum"
    assert prob["filename"] == "TwoSum.cpp"
    assert prob["language"] == "C++"
    assert prob["category"] == "Arrays"
    assert prob["folder_category"] == "Arrays"
    assert prob["status"] == "complete"
    assert prob["is_complete"] is True
    assert prob["missing_fields"] == []


def test_scan_java_file(temp_repo):
    """Scan repository with a Java solution file."""
    cat_dir = temp_repo / "Trees"
    cat_dir.mkdir()
    java_file = cat_dir / "InorderTraversal.java"

    content = backend.generate_problem_content(
        title="Inorder Traversal",
        platform="LeetCode",
        language="Java",
        category="Trees",
        description="Binary tree inorder traversal.",
        solution_code="class Solution {\n    public List<Integer> inorderTraversal() { return new ArrayList<>(); }\n}\n",
        concepts="Recursion",
        data_structures="Tree, List",
        tags="Interview",
        importance="4",
        time_complexity="O(n)",
        space_complexity="O(n)",
    )
    java_file.write_text(content, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 1
    assert res["complete_count"] == 1
    prob = res["problems"][0]
    assert prob["language"] == "Java"
    assert prob["status"] == "complete"


def test_scan_python_file(temp_repo):
    """Scan repository with a Python solution file."""
    cat_dir = temp_repo / "Math"
    cat_dir.mkdir()
    py_file = cat_dir / "CountPrimes.py"

    content = backend.generate_problem_content(
        title="Count Primes",
        platform="LeetCode",
        language="Python",
        category="Math",
        description="Count primes less than n.",
        solution_code="class Solution:\n    def countPrimes(self, n: int) -> int:\n        return 0\n",
        concepts="Sieve of Eratosthenes",
        data_structures="Array",
        tags="Pattern",
        importance="3",
        time_complexity="O(n log log n)",
        space_complexity="O(n)",
    )
    py_file.write_text(content, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 1
    assert res["complete_count"] == 1
    prob = res["problems"][0]
    assert prob["language"] == "Python"
    assert prob["status"] == "complete"


def test_scan_multiple_categories(temp_repo):
    """Scan multiple categories and files across folders."""
    for cat in ["Arrays", "Strings", "Graphs"]:
        c_dir = temp_repo / cat
        c_dir.mkdir()
        f = c_dir / f"Prob_{cat}.cpp"
        f.write_text(
            backend.generate_problem_content(
                title=f"Prob {cat}",
                platform="LeetCode",
                language="C++",
                category=cat,
                description="Sample problem",
                solution_code="// code\n",
                tags="Must-Do",
                importance=4,
            ),
            encoding="utf-8",
        )

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 3
    assert res["complete_count"] == 3


def test_scan_ignore_unrelated_files(temp_repo):
    """Scanner ignores .txt, .md, .json, .exe, etc."""
    (temp_repo / "README.md").write_text("# Notes", encoding="utf-8")
    (temp_repo / "notes.txt").write_text("todo list", encoding="utf-8")
    (temp_repo / "data.json").write_text("{}", encoding="utf-8")
    (temp_repo / "run.exe").write_bytes(b"binary")

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 0


def test_scan_ignore_git_directory(temp_repo):
    """Scanner ignores .git directory and hidden files."""
    git_dir = temp_repo / ".git"
    git_dir.mkdir()
    (git_dir / "config.cpp").write_text("// hidden file", encoding="utf-8")

    hidden_dir = temp_repo / ".vscode"
    hidden_dir.mkdir()
    (hidden_dir / "settings.py").write_text("# hidden py", encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 0


# ==============================================================================
# 2. METADATA PARSING & MISSING FIELD DETECTION
# ==============================================================================

def test_parse_missing_tags(temp_repo):
    """Detect older files where 'Tags' field is absent."""
    cat_dir = temp_repo / "Math"
    cat_dir.mkdir()
    f = cat_dir / "OldMath.cpp"

    header = """/*
==================================================
Problem: Old Math
Platform: LeetCode
Language: C++

Primary Category: Math
Concepts / Techniques: Math
Data Structures: None
Importance: 3

Time Complexity: O(1)
Space Complexity: O(1)

Added: 2026-01-01

Problem Description:
Old problem without tags.
==================================================
*/

int solution() { return 42; }
"""
    f.write_text(header, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 1
    assert res["incomplete_count"] == 1
    assert res["complete_count"] == 0
    prob = res["problems"][0]
    assert prob["status"] == "incomplete"
    assert "Tags" in prob["missing_fields"]


def test_parse_missing_importance(temp_repo):
    """Detect older files where 'Importance' field is absent."""
    cat_dir = temp_repo / "Arrays"
    cat_dir.mkdir()
    f = cat_dir / "OldArray.cpp"

    header = """/*
==================================================
Problem: Old Array
Platform: LeetCode
Language: C++

Primary Category: Arrays
Concepts / Techniques: Two Pointer
Data Structures: Array
Tags: Interview

Time Complexity: O(n)
Space Complexity: O(1)

Added: 2026-01-01

Problem Description:
Old problem without importance.
==================================================
*/

void solve() {}
"""
    f.write_text(header, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["incomplete_count"] == 1
    prob = res["problems"][0]
    assert "Importance" in prob["missing_fields"]


def test_parse_missing_data_structures(temp_repo):
    """Detect older files where 'Data Structures' field is absent."""
    cat_dir = temp_repo / "Hashing"
    cat_dir.mkdir()
    f = cat_dir / "OldHash.cpp"

    header = """/*
==================================================
Problem: Old Hash
Platform: LeetCode
Language: C++

Primary Category: Hashing
Concepts / Techniques: Map
Tags: Revision
Importance: 4

Time Complexity: O(n)
Space Complexity: O(n)

Added: 2026-01-01

Problem Description:
Old problem without Data Structures.
==================================================
*/
"""
    f.write_text(header, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["incomplete_count"] == 1
    prob = res["problems"][0]
    assert "Data Structures" in prob["missing_fields"]


def test_parse_missing_concepts_techniques(temp_repo):
    """Detect files where 'Concepts / Techniques' is absent."""
    cat_dir = temp_repo / "Strings"
    cat_dir.mkdir()
    f = cat_dir / "OldString.cpp"

    header = """/*
==================================================
Problem: Old String
Platform: LeetCode
Language: C++

Primary Category: Strings
Data Structures: String
Tags: Tricky
Importance: 2

Time Complexity: O(n)
Space Complexity: O(1)

Added: 2026-01-01

Problem Description:
Desc
==================================================
*/
"""
    f.write_text(header, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    prob = res["problems"][0]
    assert "Concepts / Techniques" in prob["missing_fields"]


def test_parse_missing_complexity(temp_repo):
    """Detect files where Time or Space complexity is missing."""
    cat_dir = temp_repo / "Math"
    cat_dir.mkdir()
    f = cat_dir / "NoComplexity.cpp"

    header = """/*
==================================================
Problem: No Complexity
Platform: LeetCode
Language: C++

Primary Category: Math
Concepts / Techniques: Math
Data Structures: Array
Tags: Interview
Importance: 3

Added: 2026-01-01

Problem Description:
Desc
==================================================
*/
"""
    f.write_text(header, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    prob = res["problems"][0]
    assert "Time Complexity" in prob["missing_fields"]
    assert "Space Complexity" in prob["missing_fields"]


def test_parse_detect_unreadable_header(temp_repo):
    """Detect files with arbitrary comments or no DSA header."""
    cat_dir = temp_repo / "Misc"
    cat_dir.mkdir()
    f = cat_dir / "RawFile.cpp"
    f.write_text("// This is a plain C++ file without a DSA header\nint main() { return 0; }\n", encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 1
    assert res["unreadable_count"] == 1
    prob = res["problems"][0]
    assert prob["status"] == "unreadable"
    assert prob["is_complete"] is False


def test_scanner_does_not_inspect_solution_code_for_keywords(temp_repo):
    """Solution code variable names like 'int importance = 5;' must NOT fool the scanner."""
    cat_dir = temp_repo / "Math"
    cat_dir.mkdir()
    f = cat_dir / "TrickyCode.cpp"

    # Header is missing Importance
    header = """/*
==================================================
Problem: Tricky Code
Platform: LeetCode
Language: C++

Primary Category: Math
Concepts / Techniques: Math
Data Structures: Array
Tags: Interview

Time Complexity: O(1)
Space Complexity: O(1)

Added: 2026-01-01

Problem Description:
Desc
==================================================
*/

void solve() {
    int importance = 5;
    string tags = "Must-Do";
}
"""
    f.write_text(header, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    prob = res["problems"][0]
    assert "Importance" in prob["missing_fields"]


# ==============================================================================
# 3. METADATA REPAIR TESTS
# ==============================================================================

def test_repair_adds_missing_fields_and_preserves_solution(temp_repo):
    """Repair an older file, verify new header, byte-for-byte solution preservation, and path unchanged."""
    cat_dir = temp_repo / "Math"
    cat_dir.mkdir()
    f = cat_dir / "TheMissingNumber.cpp"

    orig_solution = (
        "#include <iostream>\n"
        "#include <vector>\n"
        "using namespace std;\n\n"
        "int missingNumber(vector<int>& nums) {\n"
        "    int n = nums.size();\n"
        "    int sum = n * (n + 1) / 2;\n"
        "    for (int x : nums) sum -= x;\n"
        "    return sum;\n"
        "}\n"
    )

    old_content = """/*
==================================================
Problem: The Missing Number
Platform: Smart Interview
Language: C++

Primary Category: Math
Concepts / Techniques: Math
Time Complexity: O(n)
Space Complexity: O(1)

Added: 2026-01-15

Problem Description:
Find missing number in array.
==================================================
*/
""" + orig_solution

    f.write_text(old_content, encoding="utf-8")

    # Initial scan confirms incomplete (missing Tags, Importance, Data Structures)
    scan1 = backend.scan_repository(temp_repo)
    assert scan1["incomplete_count"] == 1
    assert "Tags" in scan1["problems"][0]["missing_fields"]
    assert "Importance" in scan1["problems"][0]["missing_fields"]
    assert "Data Structures" in scan1["problems"][0]["missing_fields"]

    # Repair metadata
    updated_fields = {
        "title": "The Missing Number",
        "platform": "Smart Interview",
        "language": "C++",
        "category": "Math",
        "concepts": "Hashing, Two Pointer",
        "data_structures": "Array, HashMap",
        "tags": "Interview, Revision, Tricky",
        "importance": "5",
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "added_date": "2026-01-15",
        "description": "Find missing number in array.",
    }

    ok, msg = backend.update_problem_metadata(f, updated_fields, repo_path=temp_repo)
    assert ok is True
    assert "Metadata updated successfully" in msg

    # Verify physical file
    assert f.exists()
    assert f.is_file()
    assert f.parent == cat_dir

    # Rescan repository -> must now be 100% complete
    scan2 = backend.scan_repository(temp_repo)
    assert scan2["total_problems"] == 1
    assert scan2["complete_count"] == 1
    assert scan2["incomplete_count"] == 0
    prob2 = scan2["problems"][0]
    assert prob2["status"] == "complete"
    assert prob2["missing_fields"] == []
    assert prob2["metadata"]["importance"] == "5"
    assert "Interview" in prob2["metadata"]["tags"]
    assert "Array" in prob2["metadata"]["data_structures"]

    # Verify solution code is byte-for-byte identical
    parsed = backend.parse_problem_metadata(f)
    assert parsed["solution_code"] == orig_solution


def test_repair_unreadable_file(temp_repo):
    """Repair a file that had no header at all, prepending standardized header."""
    cat_dir = temp_repo / "Arrays"
    cat_dir.mkdir()
    f = cat_dir / "RawSolution.py"
    sol = "def two_sum(nums, target):\n    return []\n"
    f.write_text(sol, encoding="utf-8")

    # Repair
    updated = {
        "title": "Raw Solution",
        "platform": "LeetCode",
        "language": "Python",
        "category": "Arrays",
        "concepts": "Hash Map",
        "data_structures": "Array",
        "tags": "Interview",
        "importance": 4,
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "added_date": "2026-09-26",
        "description": "Two sum problem",
    }

    ok, msg = backend.update_problem_metadata(f, updated, repo_path=temp_repo)
    assert ok is True

    scan = backend.scan_repository(temp_repo)
    assert scan["complete_count"] == 1
    parsed = backend.parse_problem_metadata(f)
    assert parsed["solution_code"] == sol


# ==============================================================================
# 4. CATEGORY & FOLDER CONSISTENCY & RELOCATION
# ==============================================================================

def test_scan_detects_category_mismatch_without_moving_file(temp_repo):
    """Scan detects category mismatch warning, but scan itself is read-only and never moves files."""
    folder_dir = temp_repo / "Uncategorized"
    folder_dir.mkdir()
    f = folder_dir / "MathProblem.cpp"

    content = backend.generate_problem_content(
        title="Math Problem",
        platform="LeetCode",
        language="C++",
        category="Math",  # Metadata says Math, but folder is Uncategorized
        description="Math problem",
        solution_code="// code\n",
        tags="Interview",
        importance=4,
    )
    f.write_text(content, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 1
    assert res["mismatch_count"] == 1
    prob = res["problems"][0]
    assert prob["category_mismatch"] is True
    assert prob["folder_category"] == "Uncategorized"
    assert prob["category"] == "Math"

    # Verify scan alone did NOT move the file
    assert f.exists()
    assert (temp_repo / "Uncategorized" / "MathProblem.cpp").exists()
    assert not (temp_repo / "Math" / "MathProblem.cpp").exists()


def test_repair_relocates_file_when_category_changed(temp_repo):
    """Repairing a file with a new Primary Category physically relocates the file and removes source."""
    folder_dir = temp_repo / "Uncategorized"
    folder_dir.mkdir()
    old_file = folder_dir / "MeanMedianMode.cpp"

    orig_solution = "int main() { return 0; }\n"
    content = backend.generate_problem_content(
        title="Mean Median Mode",
        platform="Smart Interview",
        language="C++",
        category="Uncategorized",
        description="Calculate mean, median and mode.",
        solution_code=orig_solution,
        tags="Interview",
        importance=3,
    )
    old_file.write_text(content, encoding="utf-8")

    # Update metadata to Primary Category: Math
    updated = {
        "title": "Mean Median Mode",
        "platform": "Smart Interview",
        "language": "C++",
        "category": "Math",  # Change category to Math
        "concepts": "Math",
        "data_structures": "Array",
        "tags": "Interview, Revision",
        "importance": 5,
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "added_date": "2026-09-25",
        "description": "Calculate mean, median and mode.",
    }

    ok, msg = backend.update_problem_metadata(old_file, updated, repo_path=temp_repo)
    assert ok is True
    assert "relocated to Math/MeanMedianMode.cpp" in msg

    # 1. Source file in Uncategorized must NOT exist
    assert not old_file.exists()

    # 2. Destination file in Math must exist
    dest_file = temp_repo / "Math" / "MeanMedianMode.cpp"
    assert dest_file.exists()
    assert dest_file.is_file()

    # 3. Read back and verify metadata
    parsed = backend.parse_problem_metadata(dest_file)
    assert parsed["category"] == "Math"
    assert parsed["importance"] == "5"
    assert parsed["tags"] == "Interview, Revision"
    assert parsed["solution_code"] == orig_solution

    # 4. Rescan repository: must be complete with 0 mismatches
    scan = backend.scan_repository(temp_repo)
    assert scan["total_problems"] == 1
    assert scan["complete_count"] == 1
    assert scan["mismatch_count"] == 0
    prob = scan["problems"][0]
    assert prob["status"] == "complete"
    assert prob["folder_category"] == "Math"
    assert prob["category"] == "Math"
    assert prob["category_mismatch"] is False


def test_repair_without_category_change_keeps_file_in_place(temp_repo):
    """Repairing without changing Primary Category updates file in place without moving."""
    folder_dir = temp_repo / "Math"
    folder_dir.mkdir()
    f = folder_dir / "CompoundInterest.cpp"

    content = backend.generate_problem_content(
        title="Compound Interest",
        platform="LeetCode",
        language="C++",
        category="Math",
        description="Calculate CI",
        solution_code="double solve() { return 0.0; }\n",
        tags="",
        importance=3,
    )
    f.write_text(content, encoding="utf-8")

    updated = {
        "title": "Compound Interest",
        "category": "Math",  # Category remains Math
        "tags": "Math, Formula",
        "importance": 4,
    }

    ok, msg = backend.update_problem_metadata(f, updated, repo_path=temp_repo)
    assert ok is True
    assert f.exists()
    assert f.parent == folder_dir


def test_repair_relocate_to_uncategorized(temp_repo):
    """Relocating a file from a category to Uncategorized works properly."""
    folder_dir = temp_repo / "Math"
    folder_dir.mkdir()
    f = folder_dir / "GenericProblem.cpp"
    f.write_text(
        backend.generate_problem_content(
            title="Generic Problem",
            platform="LeetCode",
            language="C++",
            category="Math",
            description="Desc",
            solution_code="// sol\n",
        ),
        encoding="utf-8",
    )

    updated = {
        "title": "Generic Problem",
        "category": "Uncategorized",
        "tags": "Basic",
        "importance": 2,
    }

    ok, msg = backend.update_problem_metadata(f, updated, repo_path=temp_repo)
    assert ok is True
    assert not f.exists()
    assert (temp_repo / "Uncategorized" / "GenericProblem.cpp").exists()


def test_repair_destination_collision_prevention(temp_repo):
    """Relocation is prevented when destination file already exists (no overwrite)."""
    dir1 = temp_repo / "Arrays"
    dir1.mkdir()
    f1 = dir1 / "TwoSum.cpp"
    f1.write_text("// arrays two sum\n", encoding="utf-8")

    dir2 = temp_repo / "Hashing"
    dir2.mkdir()
    f2 = dir2 / "TwoSum.cpp"
    f2.write_text("// hashing two sum\n", encoding="utf-8")

    # Attempt to relocate f1 to Hashing (where TwoSum.cpp already exists)
    updated = {
        "title": "Two Sum",
        "category": "Hashing",
    }
    ok, msg = backend.update_problem_metadata(f1, updated, repo_path=temp_repo)
    assert ok is False
    assert "Destination collision" in msg

    # Verify both original files are untouched
    assert f1.exists()
    assert f2.exists()
    assert f1.read_text(encoding="utf-8") == "// arrays two sum\n"
    assert f2.read_text(encoding="utf-8") == "// hashing two sum\n"


def test_repair_path_traversal_rejected(temp_repo):
    """Path traversal category names are rejected safely."""
    cat_dir = temp_repo / "Arrays"
    cat_dir.mkdir()
    f = cat_dir / "ProblemSafe.cpp"
    f.write_text("// safe\n", encoding="utf-8")

    updated = {
        "title": "Problem Safe",
        "category": "../../../System32",
    }
    ok, msg = backend.update_problem_metadata(f, updated, repo_path=temp_repo)
    assert ok is False
    assert "Invalid category" in msg
    assert f.exists()


def test_custom_top_level_categories(temp_repo):
    """Scanner recognizes custom top-level category folders."""
    cat_dir = temp_repo / "Trie"
    cat_dir.mkdir()
    f = cat_dir / "ImplementTrie.cpp"
    f.write_text(
        backend.generate_problem_content(
            title="Implement Trie",
            platform="LeetCode",
            language="C++",
            category="Trie",
            description="Trie implementation",
            solution_code="// trie\n",
            tags="Interview",
            importance=5,
        ),
        encoding="utf-8",
    )

    res = backend.scan_repository(temp_repo)
    assert res["total_problems"] == 1
    assert res["complete_count"] == 1
    assert res["mismatch_count"] == 0
    assert res["problems"][0]["folder_category"] == "Trie"


# ==============================================================================
# 5. TAGS & IMPORTANCE REUSE
# ==============================================================================

def test_builtin_and_custom_tags(temp_config):
    """Verify built-in tags and custom tags integration."""
    all_t = backend.get_all_tags()
    for b in backend.BUILTIN_TAGS:
        assert b in all_t

    ok, _ = backend.save_custom_tag("Google")
    assert ok is True
    assert "Google" in backend.get_all_tags()

    # Case-insensitive duplicate check
    ok_dup, dup_msg = backend.save_custom_tag("google")
    assert ok_dup is False
    assert "already" in dup_msg.lower()


def test_importance_validation():
    """Valid importance values 1-5 pass, others fail validation."""
    meta_valid = {
        "valid_header": True,
        "present_fields": [
            "Problem", "Platform", "Language", "Primary Category",
            "Concepts / Techniques", "Data Structures", "Tags",
            "Importance", "Time Complexity", "Space Complexity",
            "Added", "Problem Description",
        ],
        "title": "Title",
        "platform": "LeetCode",
        "language": "C++",
        "category": "Arrays",
        "importance": "5",
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "added_date": "2026-09-26",
    }
    val = backend.validate_problem_metadata(meta_valid)
    assert val["is_complete"] is True

    # Invalid importance
    meta_invalid = dict(meta_valid)
    meta_invalid["importance"] = "99"
    val_inv = backend.validate_problem_metadata(meta_invalid)
    assert val_inv["is_complete"] is False
    assert "Importance" in val_inv["missing_fields"]


# ==============================================================================
# 6. REPEATABILITY & IDEMPOTENCE
# ==============================================================================

def test_repeated_rescans_are_safe_and_idempotent(temp_repo):
    """Running scan multiple times does not alter repository or counts."""
    cat_dir = temp_repo / "Arrays"
    cat_dir.mkdir()
    f = cat_dir / "ProblemA.cpp"
    f.write_text(
        backend.generate_problem_content(
            title="Problem A",
            platform="LeetCode",
            language="C++",
            category="Arrays",
            description="Desc",
            solution_code="// sol\n",
            tags="Interview",
            importance=4,
        ),
        encoding="utf-8",
    )

    res1 = backend.scan_repository(temp_repo)
    res2 = backend.scan_repository(temp_repo)
    res3 = backend.scan_repository(temp_repo)

    assert res1["total_problems"] == res2["total_problems"] == res3["total_problems"] == 1
    assert res1["complete_count"] == res2["complete_count"] == res3["complete_count"] == 1
    assert res1["incomplete_count"] == res2["incomplete_count"] == res3["incomplete_count"] == 0


# ==============================================================================
# 7. ADDITIONAL DETAILED METADATA & REPAIR TESTS
# ==============================================================================

def test_present_but_empty_optional_fields_are_complete(temp_repo):
    """Optional fields (Concepts, DS, Tags) present but empty do NOT count as missing."""
    cat_dir = temp_repo / "Arrays"
    cat_dir.mkdir()
    f = cat_dir / "EmptyOptional.cpp"

    content = backend.generate_problem_content(
        title="Empty Optional",
        platform="LeetCode",
        language="C++",
        category="Arrays",
        description="Desc",
        solution_code="// sol\n",
        concepts="",
        data_structures="",
        tags="",
        importance=3,
        time_complexity="O(n)",
        space_complexity="O(1)",
    )
    f.write_text(content, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["complete_count"] == 1
    assert res["incomplete_count"] == 0
    prob = res["problems"][0]
    assert prob["status"] == "complete"
    assert prob["missing_fields"] == []


def test_missing_added_date(temp_repo):
    """Detect when 'Added' date is absent from the header."""
    cat_dir = temp_repo / "Math"
    cat_dir.mkdir()
    f = cat_dir / "NoDate.cpp"

    header = """/*
==================================================
Problem: No Date
Platform: LeetCode
Language: C++

Primary Category: Math
Concepts / Techniques: 
Data Structures: 
Tags: 
Importance: 3

Time Complexity: O(1)
Space Complexity: O(1)

Problem Description:
Desc
==================================================
*/
int x = 1;
"""
    f.write_text(header, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["incomplete_count"] == 1
    assert "Added" in res["problems"][0]["missing_fields"]


def test_repair_java_file_metadata(temp_repo):
    """Repair metadata in a Java solution file."""
    cat_dir = temp_repo / "LinkedLists"
    cat_dir.mkdir()
    java_file = cat_dir / "ReverseList.java"

    orig_code = (
        "class Solution {\n"
        "    public ListNode reverseList(ListNode head) {\n"
        "        ListNode prev = null;\n"
        "        ListNode curr = head;\n"
        "        while (curr != null) {\n"
        "            ListNode next = curr.next;\n"
        "            curr.next = prev;\n"
        "            prev = curr;\n"
        "            curr = next;\n"
        "        }\n"
        "        return prev;\n"
        "    }\n"
        "}\n"
    )

    old_content = """/*
==================================================
Problem: Reverse List
Platform: LeetCode
Language: Java

Primary Category: LinkedLists
Time Complexity: O(n)
Space Complexity: O(1)

Added: 2026-02-01

Problem Description:
Reverse a singly linked list.
==================================================
*/
""" + orig_code

    java_file.write_text(old_content, encoding="utf-8")

    # Verify initially incomplete
    scan1 = backend.scan_repository(temp_repo)
    assert scan1["incomplete_count"] == 1

    # Repair
    repair_fields = {
        "title": "Reverse Linked List",
        "platform": "LeetCode",
        "language": "Java",
        "category": "LinkedLists",
        "concepts": "Pointers",
        "data_structures": "LinkedList",
        "tags": "Must-Do, Interview",
        "importance": 5,
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "added_date": "2026-02-01",
        "description": "Reverse a singly linked list.",
    }

    ok, msg = backend.update_problem_metadata(java_file, repair_fields, repo_path=temp_repo)
    assert ok is True

    scan2 = backend.scan_repository(temp_repo)
    assert scan2["complete_count"] == 1
    assert scan2["incomplete_count"] == 0

    parsed = backend.parse_problem_metadata(java_file)
    assert parsed["solution_code"] == orig_code
    assert parsed["tags"] == "Must-Do, Interview"
    assert parsed["importance"] == "5"


def test_repair_python_file_metadata(temp_repo):
    """Repair metadata in a Python solution file with triple quotes."""
    cat_dir = temp_repo / "DynamicProgramming"
    cat_dir.mkdir()
    py_file = cat_dir / "ClimbingStairs.py"

    orig_code = (
        "class Solution:\n"
        "    def climbStairs(self, n: int) -> int:\n"
        "        a, b = 1, 1\n"
        "        for _ in range(n - 1):\n"
        "            a, b = b, a + b\n"
        "        return b\n"
    )

    old_content = '"""\nProblem: Climbing Stairs\nPlatform: LeetCode\nPrimary Category: DynamicProgramming\n"""\n' + orig_code
    py_file.write_text(old_content, encoding="utf-8")

    # Repair
    repair_fields = {
        "title": "Climbing Stairs",
        "platform": "LeetCode",
        "language": "Python",
        "category": "DynamicProgramming",
        "concepts": "Fibonacci, DP",
        "data_structures": "Variables",
        "tags": "Interview, Pattern",
        "importance": 4,
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "added_date": "2026-09-26",
        "description": "Ways to climb n stairs.",
    }

    ok, msg = backend.update_problem_metadata(py_file, repair_fields, repo_path=temp_repo)
    assert ok is True

    scan = backend.scan_repository(temp_repo)
    assert scan["complete_count"] == 1

    parsed = backend.parse_problem_metadata(py_file)
    assert parsed["solution_code"] == orig_code
    assert parsed["tags"] == "Interview, Pattern"
    assert parsed["importance"] == "4"


def test_scan_invalid_repository_path():
    """scan_repository on non-existent path gracefully returns error."""
    res = backend.scan_repository("/non/existent/path/xyz")
    assert res["success"] is False
    assert res["total_problems"] == 0
    assert "error" in res


def test_non_dsa_comment_block_treated_as_unreadable(temp_repo):
    """A generic license or author comment block without DSA keywords is unreadable."""
    cat_dir = temp_repo / "Math"
    cat_dir.mkdir()
    f = cat_dir / "GenericComment.cpp"
    content = "/*\n Copyright (c) 2026 Author\n All rights reserved.\n*/\nint solve() { return 0; }\n"
    f.write_text(content, encoding="utf-8")

    res = backend.scan_repository(temp_repo)
    assert res["unreadable_count"] == 1
    assert res["problems"][0]["status"] == "unreadable"

