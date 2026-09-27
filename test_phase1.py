"""
test_phase1.py - Automated test suite for Phase 1 requirements and acceptance criteria.
"""

import json
from pathlib import Path
import shutil
import tempfile

from engine import backend


def run_phase1_tests() -> bool:
    print("==================================================")
    print("Running Phase 1 Test Suite")
    print("==================================================")
    results = {}

    with tempfile.TemporaryDirectory() as temp_repo:
        repo_path = Path(temp_repo).resolve()

        # Test 1 & 2: Valid C++ Problem Creation & Content Verification
        print("\n[Test 1 & 2] Testing C++ problem creation and content verification...")
        t1_title = "Two Sum"
        t1_platform = "LeetCode"
        t1_language = "C++"
        t1_category = "Hashing"
        t1_desc = "Given an array of integers nums and an integer target, return indices of two numbers."
        t1_sol = "#include <bits/stdc++.h>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {}\n};"

        t1_ok, t1_msg, t1_file = backend.create_problem_file(
            title=t1_title,
            platform=t1_platform,
            language=t1_language,
            category=t1_category,
            description=t1_desc,
            solution_code=t1_sol,
            repo_path=repo_path,
        )

        expected_t1_file = repo_path / "Hashing" / "TwoSum.cpp"
        if t1_ok and expected_t1_file.exists() and expected_t1_file.is_file():
            print(f" PASS: File physically exists at {expected_t1_file}")
            results["C++ creation"] = "PASS"

            # Content verification
            content = expected_t1_file.read_text(encoding="utf-8")
            has_title = "Problem: Two Sum" in content
            has_platform = "Platform: LeetCode" in content
            has_lang = "Language: C++" in content
            has_cat = "Primary Category: Hashing" in content
            has_desc = t1_desc in content
            has_sol = t1_sol in content
            has_comment_block = content.startswith("/*") and "*/" in content

            if all([has_title, has_platform, has_lang, has_cat, has_desc, has_sol, has_comment_block]):
                print(" PASS: File content verified (header metadata + exact solution code).")
                results["Content verification"] = "PASS"
            else:
                print(" FAIL: Content mismatch in generated file.")
                results["Content verification"] = "FAIL"
        else:
            print(f" FAIL: C++ creation failed: {t1_msg}")
            results["C++ creation"] = "FAIL"
            results["Content verification"] = "FAIL"

        # Test 3: Python Problem Creation
        print("\n[Test 3] Testing Python problem creation...")
        t3_title = "Valid Parentheses"
        t3_platform = "LeetCode"
        t3_language = "Python"
        t3_category = "Stacks"
        t3_desc = "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if input is valid."
        t3_sol = "class Solution:\n    def isValid(self, s: str) -> bool:\n        return True"

        t3_ok, t3_msg, t3_file = backend.create_problem_file(
            title=t3_title,
            platform=t3_platform,
            language=t3_language,
            category=t3_category,
            description=t3_desc,
            solution_code=t3_sol,
            repo_path=repo_path,
        )

        expected_t3_file = repo_path / "Stacks" / "ValidParentheses.py"
        if t3_ok and expected_t3_file.exists() and expected_t3_file.is_file():
            t3_content = expected_t3_file.read_text(encoding="utf-8")
            if t3_content.startswith('"""') and '"""' in t3_content[3:] and t3_sol in t3_content:
                print(f" PASS: Python file exists at {expected_t3_file} with python comment header.")
                results["Python creation"] = "PASS"
            else:
                print(" FAIL: Python file header/syntax mismatch.")
                results["Python creation"] = "FAIL"
        else:
            print(f" FAIL: Python creation failed: {t3_msg}")
            results["Python creation"] = "FAIL"

        # Test 4: Java Problem Creation
        print("\n[Test 4] Testing Java problem creation...")
        t4_title = "Binary Search"
        t4_platform = "LeetCode"
        t4_language = "Java"
        t4_category = "Searching"
        t4_desc = "Given an array of integers nums which is sorted in ascending order, search for target."
        t4_sol = "class Solution {\n    public int search(int[] nums, int target) {\n        return -1;\n    }\n}"

        t4_ok, t4_msg, t4_file = backend.create_problem_file(
            title=t4_title,
            platform=t4_platform,
            language=t4_language,
            category=t4_category,
            description=t4_desc,
            solution_code=t4_sol,
            repo_path=repo_path,
        )

        expected_t4_file = repo_path / "Searching" / "BinarySearch.java"
        if t4_ok and expected_t4_file.exists() and expected_t4_file.is_file():
            t4_content = expected_t4_file.read_text(encoding="utf-8")
            if t4_content.startswith("/*") and t4_sol in t4_content:
                print(f" PASS: Java file exists at {expected_t4_file} with Java comment header.")
                results["Java creation"] = "PASS"
            else:
                print(" FAIL: Java file header/syntax mismatch.")
                results["Java creation"] = "FAIL"
        else:
            print(f" FAIL: Java creation failed: {t4_msg}")
            results["Java creation"] = "FAIL"

        # Test 5: Existing Category Folder Reuse
        print("\n[Test 5] Testing category folder reuse (no duplicate folder)...")
        # In Test 1, Hashing was created. Now add another problem to Hashing.
        t5_ok, t5_msg, _ = backend.create_problem_file(
            title="Group Anagrams",
            platform="LeetCode",
            language="C++",
            category="Hashing",
            description="Group anagrams together.",
            solution_code="// solution",
            repo_path=repo_path,
        )
        hashing_dirs = [p for p in repo_path.iterdir() if p.is_dir() and "hash" in p.name.lower()]
        if t5_ok and len(hashing_dirs) == 1 and hashing_dirs[0].name == "Hashing":
            print(f" PASS: Exactly one Hashing folder exists; reused without duplicates.")
            results["Existing category"] = "PASS"
        else:
            print(f" FAIL: Duplicate category folders found: {hashing_dirs}")
            results["Existing category"] = "FAIL"

        # Test 6: Missing Category Folder Creation
        print("\n[Test 6] Testing missing category folder creation...")
        # Trees currently does not exist
        trees_dir = repo_path / "Trees"
        assert not trees_dir.exists(), "Trees dir should not exist yet"
        t6_ok, t6_msg, _ = backend.create_problem_file(
            title="Invert Binary Tree",
            platform="LeetCode",
            language="Python",
            category="Trees",
            description="Invert tree.",
            solution_code="# invert",
            repo_path=repo_path,
        )
        tree_dirs = [p for p in repo_path.iterdir() if p.is_dir() and "tree" in p.name.lower()]
        if t6_ok and len(tree_dirs) == 1 and tree_dirs[0].name == "Trees":
            print(f" PASS: Exactly one Trees folder created: {tree_dirs[0]}")
            results["Missing category"] = "PASS"
        else:
            print(f" FAIL: Missing category folder check failed: {tree_dirs}")
            results["Missing category"] = "FAIL"

        # Test 7: Duplicate File Protection
        print("\n[Test 7] Testing duplicate file handling...")
        orig_mtime = expected_t1_file.stat().st_mtime_ns
        orig_content = expected_t1_file.read_text(encoding="utf-8")

        dup_ok, dup_msg, _ = backend.create_problem_file(
            title=t1_title,
            platform=t1_platform,
            language=t1_language,
            category=t1_category,
            description="Different description",
            solution_code="// Completely different code",
            repo_path=repo_path,
        )

        new_content = expected_t1_file.read_text(encoding="utf-8")
        if not dup_ok and "already exists" in dup_msg and new_content == orig_content:
            print(f" PASS: Duplicate creation rejected, original file preserved unchanged.")
            results["Duplicate protection"] = "PASS"
        else:
            print(f" FAIL: Duplicate file was overwritten or not rejected: {dup_msg}")
            results["Duplicate protection"] = "FAIL"

        # Test 8: Invalid Title
        print("\n[Test 8] Testing invalid title...")
        t8_ok, t8_msg, _ = backend.create_problem_file(
            title="   ",
            platform="LeetCode",
            language="C++",
            category="Arrays",
            description="Desc",
            solution_code="// code",
            repo_path=repo_path,
        )
        if not t8_ok and "title is required" in t8_msg.lower():
            print(f" PASS: Empty title cleanly rejected: '{t8_msg}'")
            results["Invalid title"] = "PASS"
        else:
            print(f" FAIL: Empty title not rejected properly: ok={t8_ok}, msg={t8_msg}")
            results["Invalid title"] = "FAIL"

        # Test 9: Invalid Repository
        print("\n[Test 9] Testing invalid repository path...")
        bad_repo = Path("C:/NonExistent_Repo_Path_123456789")
        t9_ok, t9_msg, _ = backend.create_problem_file(
            title="Valid Title",
            platform="LeetCode",
            language="C++",
            category="Arrays",
            description="Desc",
            solution_code="// code",
            repo_path=bad_repo,
        )
        if not t9_ok and "repository error" in t9_msg.lower():
            print(f" PASS: Invalid repository rejected cleanly: '{t9_msg}'")
            results["Invalid repository"] = "PASS"
        else:
            print(f" FAIL: Invalid repository not rejected: {t9_msg}")
            results["Invalid repository"] = "FAIL"

        # Test 10: Filename Sanitization
        print("\n[Test 10] Testing filename sanitization (Find: A/B?)...")
        t10_ok, t10_msg, t10_file = backend.create_problem_file(
            title="Find: A/B?",
            platform="Codeforces",
            language="C++",
            category="Arrays",
            description="Desc",
            solution_code="// code",
            repo_path=repo_path,
        )
        # Category folder should be Arrays, file should be FindAB.cpp
        arrays_dir = repo_path / "Arrays"
        expected_t10_file = arrays_dir / "FindAB.cpp"
        # Ensure no unintended subdirectories inside Arrays/
        subdirs_in_arrays = [p for p in arrays_dir.iterdir() if p.is_dir()]
        if t10_ok and expected_t10_file.exists() and len(subdirs_in_arrays) == 0:
            print(f" PASS: Sanitized to {expected_t10_file.name}, no subdirectories created.")
            results["Filename sanitization"] = "PASS"
        else:
            print(f" FAIL: Filename sanitization failed. Subdirs: {subdirs_in_arrays}, msg: {t10_msg}")
            results["Filename sanitization"] = "FAIL"

        # Test 11: Path Traversal Protection
        print("\n[Test 11] Testing path traversal protection (../../evil)...")
        # Ensure outside repository directory has no evil.cpp
        evil_outside_file = repo_path.parent / "evil.cpp"
        evil_outside_file_cat = repo_path / "evil.cpp"

        t11_ok, t11_msg, _ = backend.create_problem_file(
            title="../../evil",
            platform="LeetCode",
            language="C++",
            category="Arrays",
            description="Desc",
            solution_code="// code",
            repo_path=repo_path,
        )

        outside_escaped = evil_outside_file.exists() or evil_outside_file_cat.exists()
        if not t11_ok and not outside_escaped and "traversal" in t11_msg.lower():
            print(f" PASS: Path traversal rejected with message: '{t11_msg}'. No files created outside.")
            results["Path traversal protection"] = "PASS"
        else:
            print(f" FAIL: Path traversal check failed. ok={t11_ok}, msg={t11_msg}, outside_escaped={outside_escaped}")
            results["Path traversal protection"] = "FAIL"

    # Test 12: Phase 0 Regression
    print("\n[Test 12] Running Phase 0 regression...")
    import test_phase0
    p0_passed = test_phase0.run_all_tests()
    if p0_passed:
        results["Phase 0 regression"] = "PASS"
    else:
        results["Phase 0 regression"] = "FAIL"

    print("\n==================================================")
    print("Phase 1 Test Results Summary:")
    all_passed = True
    for test_name, status in results.items():
        print(f"  - {test_name}: {status}")
        if status != "PASS":
            all_passed = False
    print("==================================================")
    return all_passed


if __name__ == "__main__":
    success = run_phase1_tests()
    exit(0 if success else 1)
