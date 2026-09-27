"""
test_phase1_5.py - Automated test suite for Phase 1.5 requirements.

Covers:
- User-provided metadata (Category, Concepts / Techniques, Data Structures)
- Empty optional metadata handling
- Complexity analysis for Python, C++, and Java:
    - Example 1: Single loop (Time: O(n), Space: O(1))
    - Example 2: Nested loops (Time: O(n²), Space: O(1))
    - Example 3: Hash map lookup (Time: O(n), Space: O(n))
    - Example 4: Binary search (Time: O(log n), Space: O(1))
    - Example 5: Recursive solution
    - Example 6: Unsupported/ambiguous code (Unable to determine)
- Source file header embedding of complexity and metadata
- Physical file verification
- Regression verification for Phase 0 and Phase 1
"""

from pathlib import Path
import tempfile

from engine import backend
from engine.complexity import analyze_complexity


def run_phase1_5_tests() -> bool:
    print("==================================================")
    print("Running Phase 1.5 Test Suite")
    print("==================================================")
    results = {}

    # ----------------------------------------------------
    # Part 1: Complexity Analyzer Unit Tests
    # ----------------------------------------------------
    print("\n[Complexity 1] Testing single loop (Python)...")
    code1 = "for x in arr:\n    print(x)"
    res1 = analyze_complexity("Python", code1)
    if res1["time_complexity"] == "O(n)" and res1["space_complexity"] == "O(1)":
        print(f" PASS: Single loop analyzed as Time: {res1['time_complexity']}, Space: {res1['space_complexity']}")
        results["Complexity Example 1 (Single loop)"] = "PASS"
    else:
        print(f" FAIL: Unexpected complexity for single loop: {res1}")
        results["Complexity Example 1 (Single loop)"] = "FAIL"

    print("\n[Complexity 2] Testing nested loops (Python)...")
    code2 = "for i in arr:\n    for j in arr:\n        print(i, j)"
    res2 = analyze_complexity("Python", code2)
    if res2["time_complexity"] == "O(n²)" and res2["space_complexity"] == "O(1)":
        print(f" PASS: Nested loops analyzed as Time: {res2['time_complexity']}, Space: {res2['space_complexity']}")
        results["Complexity Example 2 (Nested loops)"] = "PASS"
    else:
        print(f" FAIL: Unexpected complexity for nested loops: {res2}")
        results["Complexity Example 2 (Nested loops)"] = "FAIL"

    print("\n[Complexity 3] Testing hash map lookup (Two Sum)...")
    code3 = """
seen = {}
for i, x in enumerate(nums):
    if target - x in seen:
        return [seen[target - x], i]
    seen[x] = i
"""
    res3 = analyze_complexity("Python", code3)
    if res3["time_complexity"] == "O(n)" and res3["space_complexity"] == "O(n)":
        print(f" PASS: Hash map lookup analyzed as Time: {res3['time_complexity']}, Space: {res3['space_complexity']}")
        results["Complexity Example 3 (Hash map)"] = "PASS"
    else:
        print(f" FAIL: Unexpected complexity for hash map lookup: {res3}")
        results["Complexity Example 3 (Hash map)"] = "FAIL"

    print("\n[Complexity 4] Testing binary search...")
    code4 = """
low, high = 0, len(nums) - 1
while low <= high:
    mid = (low + high) // 2
    if nums[mid] == target:
        return mid
    elif nums[mid] < target:
        low = mid + 1
    else:
        high = mid - 1
return -1
"""
    res4 = analyze_complexity("Python", code4)
    if res4["time_complexity"] == "O(log n)" and res4["space_complexity"] == "O(1)":
        print(f" PASS: Binary search analyzed as Time: {res4['time_complexity']}, Space: {res4['space_complexity']}")
        results["Complexity Example 4 (Binary search)"] = "PASS"
    else:
        print(f" FAIL: Unexpected complexity for binary search: {res4}")
        results["Complexity Example 4 (Binary search)"] = "FAIL"

    print("\n[Complexity 5] Testing recursive solution...")
    code5 = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""
    res5 = analyze_complexity("Python", code5)
    if "O(2^n)" in res5["time_complexity"] and res5["space_complexity"] == "O(n)":
        print(f" PASS: Recursive solution analyzed as Time: {res5['time_complexity']}, Space: {res5['space_complexity']}")
        results["Complexity Example 5 (Recursion)"] = "PASS"
    else:
        print(f" FAIL: Unexpected complexity for recursion: {res5}")
        results["Complexity Example 5 (Recursion)"] = "FAIL"

    print("\n[Complexity 6] Testing unsupported/ambiguous code...")
    code6 = "??? random invalid unparseable text ;;"
    res6 = analyze_complexity("Python", code6)
    if res6["time_complexity"] == "Unable to determine" and res6["space_complexity"] == "Unable to determine":
        print(f" PASS: Ambiguous code returns 'Unable to determine', no fabricated complexity.")
        results["Complexity Example 6 (Ambiguous code)"] = "PASS"
    else:
        print(f" FAIL: Ambiguous code returned fabricated complexity: {res6}")
        results["Complexity Example 6 (Ambiguous code)"] = "FAIL"

    # ----------------------------------------------------
    # Part 2: End-to-End File Creation & Metadata Verification
    # ----------------------------------------------------
    with tempfile.TemporaryDirectory() as temp_repo:
        repo_path = Path(temp_repo).resolve()

        print("\n[Metadata 1] Testing problem creation with user metadata & engine complexity (C++)...")
        t_title = "Two Sum"
        t_platform = "LeetCode"
        t_lang = "C++"
        t_cat = "Arrays"
        t_concepts = "Hashing, Two Pointer"
        t_ds = "Array, HashMap"
        t_desc = "Given an array of integers nums and an integer target..."
        t_code = """#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        unordered_map<int, int> seen;
        for (int i = 0; i < nums.size(); ++i) {
            int comp = target - nums[i];
            if (seen.count(comp)) return {seen[comp], i};
            seen[nums[i]] = i;
        }
        return {};
    }
};"""

        ok, msg, created_file = backend.create_problem_file(
            title=t_title,
            platform=t_platform,
            language=t_lang,
            category=t_cat,
            description=t_desc,
            solution_code=t_code,
            repo_path=repo_path,
            concepts=t_concepts,
            data_structures=t_ds,
        )

        if ok and created_file and created_file.exists():
            content = created_file.read_text(encoding="utf-8")
            checks = [
                "Primary Category: Arrays" in content,
                "Concepts / Techniques: Hashing, Two Pointer" in content,
                "Data Structures: Array, HashMap" in content,
                "Time Complexity: O(n)" in content,
                "Space Complexity: O(n)" in content,
                t_desc in content,
                t_code in content,
            ]
            if all(checks):
                print(f" PASS: User metadata and engine complexity verified physically in {created_file.name}")
                results["User metadata preserved"] = "PASS"
                results["Engine complexity in header"] = "PASS"
            else:
                print(f" FAIL: Header verification failed in content: {content[:350]}")
                results["User metadata preserved"] = "FAIL"
                results["Engine complexity in header"] = "FAIL"
        else:
            print(f" FAIL: File creation failed: {msg}")
            results["User metadata preserved"] = "FAIL"
            results["Engine complexity in header"] = "FAIL"

        print("\n[Metadata 2] Testing empty optional metadata (Python)...")
        t2_title = "Empty Metadata Test"
        t2_code = "for x in arr:\n    print(x)"
        ok2, msg2, file2 = backend.create_problem_file(
            title=t2_title,
            platform="Codeforces",
            language="Python",
            category="Arrays",
            description="Testing empty optional concepts and data structures.",
            solution_code=t2_code,
            repo_path=repo_path,
            concepts="",
            data_structures="",
        )

        if ok2 and file2 and file2.exists():
            content2 = file2.read_text(encoding="utf-8")
            if "Concepts / Techniques:" in content2 and "Data Structures:" in content2:
                print(" PASS: Empty optional metadata handled cleanly without artificial values.")
                results["Empty optional metadata"] = "PASS"
            else:
                print(" FAIL: Empty optional metadata missing from header.")
                results["Empty optional metadata"] = "FAIL"
        else:
            print(f" FAIL: Creation with empty metadata failed: {msg2}")
            results["Empty optional metadata"] = "FAIL"

        print("\n[Multi-Language] Testing Java complexity and header generation...")
        t3_title = "Binary Search Java"
        t3_code = """class Solution {
    public int search(int[] nums, int target) {
        int low = 0, high = nums.length - 1;
        while (low <= high) {
            int mid = low + (high - low) / 2;
            if (nums[mid] == target) return mid;
            else if (nums[mid] < target) low = mid + 1;
            else high = mid - 1;
        }
        return -1;
    }
}"""
        ok3, msg3, file3 = backend.create_problem_file(
            title=t3_title,
            platform="LeetCode",
            language="Java",
            category="Searching",
            description="Binary Search in Java",
            solution_code=t3_code,
            repo_path=repo_path,
            concepts="Binary Search",
            data_structures="Array",
        )

        if ok3 and file3 and file3.exists():
            content3 = file3.read_text(encoding="utf-8")
            if "Time Complexity: O(log n)" in content3 and "Space Complexity: O(1)" in content3:
                print(" PASS: Java binary search complexity analyzed and verified physically.")
                results["Java complexity & header"] = "PASS"
            else:
                print(f" FAIL: Java complexity mismatch in content: {content3[:350]}")
                results["Java complexity & header"] = "FAIL"
        else:
            print(f" FAIL: Java creation failed: {msg3}")
            results["Java complexity & header"] = "FAIL"

    # ----------------------------------------------------
    # Part 3: Regression Tests
    # ----------------------------------------------------
    print("\n[Regression] Running Phase 0 regression...")
    import test_phase0
    p0_pass = test_phase0.run_all_tests()
    results["Phase 0 regression"] = "PASS" if p0_pass else "FAIL"

    print("\n[Regression] Running Phase 1 regression...")
    import test_phase1
    p1_pass = test_phase1.run_phase1_tests()
    results["Phase 1 regression"] = "PASS" if p1_pass else "FAIL"

    print("\n==================================================")
    print("Phase 1.5 Test Results Summary:")
    all_passed = True
    for test_name, status in results.items():
        print(f"  - {test_name}: {status}")
        if status != "PASS":
            all_passed = False
    print("==================================================")
    return all_passed


if __name__ == "__main__":
    success = run_phase1_5_tests()
    exit(0 if success else 1)
