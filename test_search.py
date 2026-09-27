"""
test_search.py - Automated test suite for Phase 6: Search Feature & VS Code Integration.

Tests verify:
1. Basic search: empty query, title, platform, category, language, concepts, data structures, tags, importance, case-insensitivity.
2. Combined filters: category+platform, category+tag, language+importance, multiple filters.
3. Strict metadata scope: terms ONLY inside solution implementation do NOT produce matches; metadata terms DO match.
4. Category browser: filtering by category returns matching category problems.
5. VS Code path validation: valid repo file, nonexistent file, path traversal / outside repo, unsupported extensions.
"""

from pathlib import Path
import pytest
import tempfile

from engine import backend


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository directory."""
    repo_dir = tmp_path / "TestDSA"
    repo_dir.mkdir()
    return repo_dir


def create_sample_file(
    repo_dir: Path,
    rel_path: str,
    title: str = "Two Sum",
    platform: str = "LeetCode",
    language: str = "C++",
    category: str = "Arrays",
    added_date: str = "2026-09-26",
    tags: str = "Interview, Must-Do",
    concepts: str = "Two Pointers, Hashing",
    data_structures: str = "Array, HashMap",
    importance: str = "5",
    time_complexity: str = "O(n)",
    space_complexity: str = "O(n)",
    description: str = "Find two numbers that add up to target.",
    code: str = "// Solution code here\nint main() { return 0; }",
) -> Path:
    target = repo_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    content = backend.generate_problem_content(
        title=title,
        platform=platform,
        language=language,
        category=category,
        description=description,
        solution_code=code,
        created_date=added_date,
        concepts=concepts,
        data_structures=data_structures,
        time_complexity=time_complexity,
        space_complexity=space_complexity,
        tags=tags,
        importance=importance,
    )
    target.write_text(content, encoding="utf-8")
    return target


# ==============================================================================
# 1. BASIC SEARCH TESTS
# ==============================================================================

def test_empty_query_returns_all_problems(temp_repo):
    """1. Empty query returns all recognized problems in repository."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="Two Sum", category="Arrays")
    create_sample_file(temp_repo, "Strings/P2.cpp", title="Valid Anagram", category="Strings")
    create_sample_file(temp_repo, "Math/P3.cpp", title="Mean Median Mode", category="Math")

    res = backend.search_problems(temp_repo, query="")
    assert res["success"] is True
    assert res["total_matching"] == 3
    assert len(res["results"]) == 3


def test_title_search(temp_repo):
    """2. Search by problem title."""
    create_sample_file(temp_repo, "Arrays/TwoSum.cpp", title="Two Sum")
    create_sample_file(temp_repo, "Arrays/ThreeSum.cpp", title="Three Sum")
    create_sample_file(temp_repo, "Trees/Inorder.cpp", title="Binary Tree Inorder")

    res = backend.search_problems(temp_repo, query="Two Sum")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "Two Sum"


def test_platform_search(temp_repo):
    """3. Search by platform."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", platform="LeetCode")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P3.cpp", title="P3", platform="Codeforces")

    res = backend.search_problems(temp_repo, query="Smart Interview")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "P2"


def test_category_search(temp_repo):
    """4. Search by primary category."""
    create_sample_file(temp_repo, "Graphs/Dijkstra.cpp", title="Dijkstra", category="Graphs")
    create_sample_file(temp_repo, "Trees/BST.cpp", title="BST", category="Trees")

    res = backend.search_problems(temp_repo, query="Graphs")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "Dijkstra"


def test_language_search(temp_repo):
    """5. Search by programming language."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", language="C++")
    create_sample_file(temp_repo, "Arrays/P2.java", title="P2", language="Java")
    create_sample_file(temp_repo, "Arrays/P3.py", title="P3", language="Python")

    res = backend.search_problems(temp_repo, query="Python")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "P3"


def test_concepts_search(temp_repo):
    """6. Search by concepts / techniques."""
    create_sample_file(temp_repo, "Searching/BS.cpp", title="BS", concepts="Binary Search, Divide and Conquer")
    create_sample_file(temp_repo, "Arrays/Kadane.cpp", title="Kadane", concepts="Dynamic Programming, Prefix Sum")

    res = backend.search_problems(temp_repo, query="Divide and Conquer")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "BS"


def test_data_structures_search(temp_repo):
    """7. Search by data structures."""
    create_sample_file(temp_repo, "Stacks/MinStack.cpp", title="Min Stack", data_structures="Monotonic Stack")
    create_sample_file(temp_repo, "Trees/Trie.cpp", title="Trie", data_structures="Prefix Tree")

    res = backend.search_problems(temp_repo, query="Monotonic Stack")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "Min Stack"


def test_tags_search(temp_repo):
    """8. Search by tags."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", tags="Revision, Tricky")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", tags="Must-Do, Interview")

    res = backend.search_problems(temp_repo, query="Tricky")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "P1"


def test_importance_filter(temp_repo):
    """9. Filter by importance level."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", importance="5")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", importance="3")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", importance="1")

    res = backend.search_problems(temp_repo, importance="5")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "P1"


def test_case_insensitive_search(temp_repo):
    """10. Search is case-insensitive."""
    create_sample_file(temp_repo, "Math/MeanMedian.cpp", title="Mean Median Mode", concepts="Statistical Analysis")

    res1 = backend.search_problems(temp_repo, query="mean median")
    res2 = backend.search_problems(temp_repo, query="MEAN MEDIAN")
    res3 = backend.search_problems(temp_repo, query="sTaTiStIcAl")
    assert res1["total_matching"] == 1
    assert res2["total_matching"] == 1
    assert res3["total_matching"] == 1


# ==============================================================================
# 2. COMBINED FILTERS
# ==============================================================================

def test_combined_category_and_platform(temp_repo):
    """11. Combined Category + Platform filter."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="P1", category="Math", platform="LeetCode")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", category="Arrays", platform="LeetCode")

    res = backend.search_problems(temp_repo, category="Math", platform="Smart Interview")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "P2"


def test_combined_category_and_tag(temp_repo):
    """12. Combined Category + Tag filter."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", category="Arrays", tags="Must-Do")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", category="Arrays", tags="Revision")
    create_sample_file(temp_repo, "Strings/P3.cpp", title="P3", category="Strings", tags="Must-Do")

    res = backend.search_problems(temp_repo, category="Arrays", tags="Must-Do")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "P1"


def test_combined_language_and_importance(temp_repo):
    """13. Combined Language + Importance filter."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", language="C++", importance="5")
    create_sample_file(temp_repo, "Arrays/P2.py", title="P2", language="Python", importance="5")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", language="C++", importance="3")

    res = backend.search_problems(temp_repo, language="Python", importance="5")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "P2"


def test_combined_multiple_filters_together(temp_repo):
    """14. Multiple filters applied simultaneously."""
    create_sample_file(
        temp_repo,
        "Math/P1.cpp",
        title="Prime Sieve",
        category="Math",
        platform="LeetCode",
        language="C++",
        tags="Must-Do",
        concepts="Number Theory",
        importance="5",
    )
    create_sample_file(
        temp_repo,
        "Math/P2.cpp",
        title="GCD",
        category="Math",
        platform="Codeforces",
        language="C++",
        tags="Revision",
        importance="5",
    )

    res = backend.search_problems(
        temp_repo,
        query="Prime",
        category="Math",
        platform="LeetCode",
        language="C++",
        tags="Must-Do",
        importance="5",
    )
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "Prime Sieve"


# ==============================================================================
# 3. STRICT METADATA SCOPE (SOURCE CODE ISOLATION)
# ==============================================================================

def test_source_code_only_term_does_not_match(temp_repo):
    """15. Terms appearing ONLY in solution implementation code MUST NOT match."""
    # File has 'unordered_map' in solution code, but NOT in metadata header
    create_sample_file(
        temp_repo,
        "Arrays/TwoSum.cpp",
        title="Two Sum",
        category="Arrays",
        concepts="Two Pointers",
        data_structures="Array",
        tags="Interview",
        code="""#include <unordered_map>
using namespace std;
unordered_map<int, int> lookup_table_secret_keyword;
int main() { return 0; }""",
    )

    # Searching for term in solution code
    res = backend.search_problems(temp_repo, query="lookup_table_secret_keyword")
    assert res["total_matching"] == 0
    assert res["results"] == []

    res2 = backend.search_problems(temp_repo, query="unordered_map")
    assert res2["total_matching"] == 0


def test_metadata_term_does_match(temp_repo):
    """16. Terms appearing in structured metadata DO match."""
    create_sample_file(
        temp_repo,
        "Arrays/TwoSum.cpp",
        title="Two Sum",
        category="Arrays",
        concepts="Hashing",
        data_structures="HashMap",
        tags="Interview",
        code="int main() { return 0; }",
    )

    res = backend.search_problems(temp_repo, query="HashMap")
    assert res["total_matching"] == 1
    assert res["results"][0]["title"] == "Two Sum"


# ==============================================================================
# 4. CATEGORY BROWSER & FILE PATHS
# ==============================================================================

def test_category_browser_filtering(temp_repo):
    """17. Category browser aggregates and filters correctly."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="P1", category="Math")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", category="Math")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", category="Arrays")

    res_all = backend.search_problems(temp_repo)
    assert res_all["category_counts"] == {"Math": 2, "Arrays": 1}

    res_math = backend.search_problems(temp_repo, category="Math")
    assert res_math["total_matching"] == 2
    assert all(r["category"] == "Math" for r in res_math["results"])


def test_correct_physical_file_paths_returned(temp_repo):
    """18. Physical file paths returned by search are exact and exist on disk."""
    f = create_sample_file(temp_repo, "Math/MeanMedian.cpp", title="Mean Median Mode", category="Math")
    res = backend.search_problems(temp_repo, query="Mean Median")
    assert res["total_matching"] == 1
    returned_path = Path(res["results"][0]["file_path"])
    assert returned_path.resolve() == f.resolve()
    assert returned_path.exists()
    assert returned_path.is_file()


def test_unsupported_files_ignored_in_search(temp_repo):
    """19. Non-source files (.txt, .md, .git) are ignored during search."""
    create_sample_file(temp_repo, "Arrays/TwoSum.cpp", title="Two Sum")
    (temp_repo / "README.md").write_text("Problem: Two Sum", encoding="utf-8")
    (temp_repo / "notes.txt").write_text("Problem: Two Sum", encoding="utf-8")

    res = backend.search_problems(temp_repo, query="Two Sum")
    assert res["total_matching"] == 1


# ==============================================================================
# 5. VS CODE OPENING & PATH VALIDATION
# ==============================================================================

def test_validate_file_for_open_valid_file(temp_repo):
    """20. Valid repository problem file passes open validation."""
    f = create_sample_file(temp_repo, "Math/TwoSum.cpp", title="Two Sum")
    ok, msg, p = backend.validate_file_for_open(temp_repo, f)
    assert ok is True
    assert p == f.resolve()


def test_validate_file_for_open_nonexistent_file(temp_repo):
    """21. Nonexistent file is rejected with clear refresh instruction."""
    fake_path = temp_repo / "Math" / "Ghost.cpp"
    ok, msg, p = backend.validate_file_for_open(temp_repo, fake_path)
    assert ok is False
    assert "no longer exists" in msg.lower()


def test_validate_file_for_open_outside_repository(temp_repo, tmp_path):
    """22. File outside configured repository is rejected for security."""
    outside_dir = tmp_path / "Outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "Secret.cpp"
    outside_file.write_text("int main() {}", encoding="utf-8")

    ok, msg, p = backend.validate_file_for_open(temp_repo, outside_file)
    assert ok is False
    assert "outside the configured repository" in msg.lower()


def test_validate_file_for_open_unsupported_extension(temp_repo):
    """23. File with unsupported extension is rejected."""
    bad_file = temp_repo / "Math" / "notes.exe"
    bad_file.parent.mkdir(parents=True, exist_ok=True)
    bad_file.write_text("dummy", encoding="utf-8")

    ok, msg, p = backend.validate_file_for_open(temp_repo, bad_file)
    assert ok is False
    assert "unsupported file extension" in msg.lower()


# ==============================================================================
# 6. DYNAMIC FILTER CONSISTENCY & SMART INTERVIEW REGRESSION TESTS
# ==============================================================================

def test_smart_interview_dynamic_filtering_consistency(temp_repo):
    """24. Platform filter matches all problems from that platform consistently (Smart Interview regression)."""
    # 5 Smart Interview problems across different categories, 1 LeetCode problem
    create_sample_file(temp_repo, "Math/P1.cpp", title="P1", platform="Smart Interview", category="Math")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", platform="Smart Interview", category="Math")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", platform="Smart Interview", category="Arrays")
    create_sample_file(temp_repo, "Hashing/P4.cpp", title="P4", platform="Smart Interview", category="Hashing")
    create_sample_file(temp_repo, "Searching/P5.cpp", title="P5", platform="Smart Interview", category="Searching")
    create_sample_file(temp_repo, "Math/P6.cpp", title="P6", platform="LeetCode", category="Math")

    # 1. No filter -> all 6
    res_all = backend.search_problems(temp_repo)
    assert res_all["total_matching"] == 6
    assert res_all["total_repository"] == 6

    # 2. Platform = Smart Interview -> 5
    res_si = backend.search_problems(temp_repo, platform="Smart Interview")
    assert res_si["total_matching"] == 5
    assert all(r["platform"] == "Smart Interview" for r in res_si["results"])

    # 3. Platform = LeetCode -> 1
    res_lc = backend.search_problems(temp_repo, platform="LeetCode")
    assert res_lc["total_matching"] == 1
    assert res_lc["results"][0]["title"] == "P6"

    # 4. Platform = Smart Interview + Category = Math -> 2
    res_si_math = backend.search_problems(temp_repo, platform="Smart Interview", category="Math")
    assert res_si_math["total_matching"] == 2
    assert {r["title"] for r in res_si_math["results"]} == {"P1", "P2"}


def test_platform_whitespace_and_case_normalization(temp_repo):
    """25. Platform filter ignores leading/trailing whitespace and case differences."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="P1", platform="Smart Interview ")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", platform="  Smart Interview")

    res1 = backend.search_problems(temp_repo, platform="Smart Interview")
    assert res1["total_matching"] == 2

    res2 = backend.search_problems(temp_repo, platform="smart interview")
    assert res2["total_matching"] == 2

    res3 = backend.search_problems(temp_repo, platform="SMART INTERVIEW ")
    assert res3["total_matching"] == 2


def test_dynamic_filter_options_populated_from_repo_records(temp_repo):
    """26. Filter options dropdown list is derived from actual repository records."""
    create_sample_file(temp_repo, "Graphs/P1.cpp", title="P1", category="Graphs", platform="CustomJudge")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", category="Math", platform="Smart Interview")

    res = backend.search_problems(temp_repo)
    opts = res["filter_options"]

    assert "Graphs" in opts["categories"]
    assert "Math" in opts["categories"]
    assert "CustomJudge" in opts["platforms"]
    assert "Smart Interview" in opts["platforms"]


def test_multi_tag_token_filtering(temp_repo):
    """27. Multi-value comma-separated tags filter matches individual tokens."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", tags="Interview, Revision, Tricky")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", tags="Revision, Easy")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", tags="Interview, Must-Do")

    res_rev = backend.search_problems(temp_repo, tags="Revision")
    assert res_rev["total_matching"] == 2
    assert {r["title"] for r in res_rev["results"]} == {"P1", "P2"}

    res_tri = backend.search_problems(temp_repo, tags="Tricky")
    assert res_tri["total_matching"] == 1
    assert res_tri["results"][0]["title"] == "P1"

    res_int = backend.search_problems(temp_repo, tags="interview")
    assert res_int["total_matching"] == 2
    assert {r["title"] for r in res_int["results"]} == {"P1", "P3"}


def test_open_file_with_system_supported_extensions(temp_repo, monkeypatch):
    """28. open_file_with_system validates .cpp, .java, and .py files safely."""
    f_cpp = create_sample_file(temp_repo, "Math/P1.cpp", title="P1", language="C++")
    f_java = create_sample_file(temp_repo, "Math/P2.java", title="P2", language="Java")
    f_py = create_sample_file(temp_repo, "Math/P3.py", title="P3", language="Python")

    # Mock subprocess.Popen to prevent launching external applications
    launched_cmds = []
    def mock_popen(cmd, *args, **kwargs):
        launched_cmds.append(cmd)
        class DummyProcess:
            returncode = 0
        return DummyProcess()

    monkeypatch.setattr(backend.subprocess, "Popen", mock_popen)

    # 1. C++ file
    ok_cpp, msg_cpp = backend.open_file_with_system(f_cpp, temp_repo)
    assert ok_cpp is True
    assert len(launched_cmds) == 1

    # 2. Java file
    ok_java, msg_java = backend.open_file_with_system(f_java, temp_repo)
    assert ok_java is True
    assert len(launched_cmds) == 2

    # 3. Python file
    ok_py, msg_py = backend.open_file_with_system(f_py, temp_repo)
    assert ok_py is True
    assert len(launched_cmds) == 3


def test_open_file_with_system_rejects_invalid_files(temp_repo):
    """29. open_file_with_system rejects nonexistent and outside files."""
    ok, msg = backend.open_file_with_system(temp_repo / "Ghost.cpp", temp_repo)
    assert ok is False
    assert "no longer exists" in msg.lower()
