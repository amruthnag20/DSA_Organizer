"""
test_topic_view.py - Automated test suite for Phase 7: Topic / Category View.

Tests verify:
1. Category selection:
   - Math category returns only Math problems.
   - Arrays category returns only Arrays problems.
   - Uncategorized works.
   - Empty category works without crash.
2. Counts:
   - Correct problem count.
   - Correct platform counts.
   - Correct language counts.
3. Ordering:
   - Problems are sorted newest first.
   - Equal-date ordering is deterministic (alphabetical by title).
4. Normalization:
   - Category matching is case/whitespace normalized.
   - Distinct category names remain distinct.
5. Metadata:
   - Missing Added date does not crash.
   - Missing optional metadata does not crash.
   - Category mismatch does not silently move a file.
6. Integration:
   - Home category count matches Category View.
   - Search category results match Category View.
   - Add Problem updates Category View.
   - Rescan updates Category View.
"""

from pathlib import Path
import pytest
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
    title: str = "Sample Problem",
    platform: str = "LeetCode",
    language: str = "C++",
    category: str = "Math",
    added_date: str = "2026-09-26",
    tags: str = "Math, Geometry",
    concepts: str = "Number Theory",
    data_structures: str = "Array",
    importance: str = "5",
    time_complexity: str = "O(1)",
    space_complexity: str = "O(1)",
    description: str = "Sample problem description.",
    code: str = "// Solution code\nint main() { return 0; }",
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
# 1. CATEGORY SELECTION TESTS
# ==============================================================================

def test_math_category_returns_only_math_problems(temp_repo):
    """1. Math category returns strictly Math problems."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="Compound Interest", category="Math")
    create_sample_file(temp_repo, "Math/P2.cpp", title="Mean Median Mode", category="Math")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="Two Sum", category="Arrays")
    create_sample_file(temp_repo, "Strings/P4.cpp", title="Valid Anagram", category="Strings")

    res = backend.get_category_view(temp_repo, "Math")
    assert res["success"] is True
    assert res["category"] == "Math"
    assert res["problem_count"] == 2
    titles = [p["title"] for p in res["problems"]]
    assert "Compound Interest" in titles
    assert "Mean Median Mode" in titles
    assert "Two Sum" not in titles
    assert "Valid Anagram" not in titles


def test_arrays_category_returns_only_arrays_problems(temp_repo):
    """2. Arrays category returns strictly Arrays problems."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="Two Sum", category="Arrays")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="Max Subarray", category="Arrays")
    create_sample_file(temp_repo, "Math/P3.cpp", title="Prime Factors", category="Math")

    res = backend.get_category_view(temp_repo, "Arrays")
    assert res["success"] is True
    assert res["category"] == "Arrays"
    assert res["problem_count"] == 2
    titles = [p["title"] for p in res["problems"]]
    assert "Two Sum" in titles
    assert "Max Subarray" in titles
    assert "Prime Factors" not in titles


def test_uncategorized_category_works(temp_repo):
    """3. Uncategorized category is valid and returns uncategorized problems."""
    create_sample_file(temp_repo, "Uncategorized/P1.cpp", title="Mystery Problem", category="Uncategorized")
    create_sample_file(temp_repo, "Math/P2.cpp", title="Math Problem", category="Math")

    res = backend.get_category_view(temp_repo, "Uncategorized")
    assert res["success"] is True
    assert res["category"] == "Uncategorized"
    assert res["problem_count"] == 1
    assert res["problems"][0]["title"] == "Mystery Problem"


def test_empty_category_works_gracefully(temp_repo):
    """4. Querying an empty category returns 0 problems and empty stats without crashing."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="Math Problem", category="Math")

    res = backend.get_category_view(temp_repo, "Graphs")
    assert res["success"] is True
    assert res["category"] == "Graphs"
    assert res["problem_count"] == 0
    assert res["platform_counts"] == {}
    assert res["language_counts"] == {}
    assert res["latest_added"] is None
    assert res["problems"] == []


# ==============================================================================
# 2. CATEGORY STATS & COUNTS TESTS
# ==============================================================================

def test_correct_category_problem_count(temp_repo):
    """5. Correct category problem count."""
    for i in range(5):
        create_sample_file(temp_repo, f"Math/P{i}.cpp", title=f"Math Problem {i}", category="Math")

    res = backend.get_category_view(temp_repo, "Math")
    assert res["problem_count"] == 5
    assert len(res["problems"]) == 5


def test_correct_platform_counts(temp_repo):
    """6. Correct platform counts breakdown within category."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="P1", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P3.cpp", title="P3", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P4.cpp", title="P4", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P5.cpp", title="P5", category="Math", platform="LeetCode")

    res = backend.get_category_view(temp_repo, "Math")
    assert res["platform_counts"]["Smart Interview"] == 4
    assert res["platform_counts"]["LeetCode"] == 1


def test_correct_language_counts(temp_repo):
    """7. Correct language counts breakdown within category."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="P1", category="Math", language="C++")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", category="Math", language="C++")
    create_sample_file(temp_repo, "Math/P3.java", title="P3", category="Math", language="Java")
    create_sample_file(temp_repo, "Math/P4.py", title="P4", category="Math", language="Python")

    res = backend.get_category_view(temp_repo, "Math")
    assert res["language_counts"]["C++"] == 2
    assert res["language_counts"]["Java"] == 1
    assert res["language_counts"]["Python"] == 1


# ==============================================================================
# 3. ORDERING TESTS
# ==============================================================================

def test_problems_sorted_newest_first(temp_repo):
    """8. Problems are sorted newest first using Added metadata date."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="Older Problem", category="Math", added_date="2026-09-20")
    create_sample_file(temp_repo, "Math/P2.cpp", title="Middle Problem", category="Math", added_date="2026-09-24")
    create_sample_file(temp_repo, "Math/P3.cpp", title="Newest Problem", category="Math", added_date="2026-09-26")

    res = backend.get_category_view(temp_repo, "Math")
    titles = [p["title"] for p in res["problems"]]
    assert titles == ["Newest Problem", "Middle Problem", "Older Problem"]
    assert res["latest_added"] == "September 26, 2026"


def test_equal_date_ordering_deterministic(temp_repo):
    """9. Problems with equal added dates have deterministic secondary alphabetical sort."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="Zebra Math", category="Math", added_date="2026-09-25")
    create_sample_file(temp_repo, "Math/P2.cpp", title="Alpha Math", category="Math", added_date="2026-09-25")
    create_sample_file(temp_repo, "Math/P3.cpp", title="Beta Math", category="Math", added_date="2026-09-25")

    res = backend.get_category_view(temp_repo, "Math")
    titles = [p["title"] for p in res["problems"]]
    assert titles == ["Alpha Math", "Beta Math", "Zebra Math"]


# ==============================================================================
# 4. NORMALIZATION TESTS
# ==============================================================================

def test_category_matching_case_whitespace_normalized(temp_repo):
    """10. Category matching is case- and whitespace-insensitive."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="P1", category="Math")
    create_sample_file(temp_repo, "Math/P2.cpp", title="P2", category="math")
    create_sample_file(temp_repo, "Math/P3.cpp", title="P3", category=" MATH ")

    res = backend.get_category_view(temp_repo, "math")
    assert res["success"] is True
    assert res["category"] == "Math"
    assert res["problem_count"] == 3


def test_distinct_category_names_remain_distinct(temp_repo):
    """11. Distinct category names (e.g. Math vs Mathematics) remain distinct."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="P1", category="Math")
    create_sample_file(temp_repo, "Mathematics/P2.cpp", title="P2", category="Mathematics")

    res_math = backend.get_category_view(temp_repo, "Math")
    assert res_math["problem_count"] == 1
    assert res_math["problems"][0]["title"] == "P1"

    res_mathematics = backend.get_category_view(temp_repo, "Mathematics")
    assert res_mathematics["problem_count"] == 1
    assert res_mathematics["problems"][0]["title"] == "P2"


# ==============================================================================
# 5. METADATA ROBUSTNESS & MISMATCH TESTS
# ==============================================================================

def test_missing_added_date_does_not_crash(temp_repo):
    """12. Problem with missing Added date sorts gracefully and does not crash."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="With Date", category="Math", added_date="2026-09-26")
    create_sample_file(temp_repo, "Math/P2.cpp", title="Without Date", category="Math", added_date="")

    res = backend.get_category_view(temp_repo, "Math")
    assert res["success"] is True
    assert res["problem_count"] == 2
    # Problem with date comes before problem without date
    assert res["problems"][0]["title"] == "With Date"
    assert res["problems"][1]["title"] == "Without Date"


def test_missing_optional_metadata_does_not_crash(temp_repo):
    """13. Problem with older/minimal metadata does not crash Topic View."""
    p = temp_repo / "Math" / "Legacy.cpp"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("// Problem: Legacy\n// Platform: LeetCode\n// Language: C++\n// Primary Category: Math\nint x;", encoding="utf-8")

    res = backend.get_category_view(temp_repo, "Math")
    assert res["success"] is True
    assert res["problem_count"] == 1
    assert res["problems"][0]["title"] == "Legacy"
    assert res["problems"][0]["tags"] == ""


def test_category_mismatch_does_not_silently_move_file(temp_repo):
    """14. Category mismatch retains file location and follows metadata category."""
    # Physical folder: Math, Primary Category metadata: Arrays
    mismatch_file = temp_repo / "Math" / "Misplaced.cpp"
    mismatch_file.parent.mkdir(parents=True, exist_ok=True)
    content = backend.generate_problem_content(
        title="Misplaced Problem",
        platform="LeetCode",
        language="C++",
        category="Arrays",
        description="Folder is Math, Category is Arrays",
        solution_code="int main() {}",
    )
    mismatch_file.write_text(content, encoding="utf-8")

    # Authoritative Primary Category is Arrays
    res_arrays = backend.get_category_view(temp_repo, "Arrays")
    assert res_arrays["problem_count"] == 1
    assert res_arrays["problems"][0]["title"] == "Misplaced Problem"

    # Math category does NOT include it
    res_math = backend.get_category_view(temp_repo, "Math")
    assert res_math["problem_count"] == 0

    # Physical file was NOT moved
    assert mismatch_file.exists()
    assert (temp_repo / "Math" / "Misplaced.cpp").is_file()


# ==============================================================================
# 6. INTEGRATION CONSISTENCY TESTS
# ==============================================================================

def test_home_category_count_matches_category_view(temp_repo):
    """15. Home dashboard category count equals Category View problem count."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="Math 1", category="Math")
    create_sample_file(temp_repo, "Math/P2.cpp", title="Math 2", category="Math")
    create_sample_file(temp_repo, "Math/P3.cpp", title="Math 3", category="Math")
    create_sample_file(temp_repo, "Arrays/P4.cpp", title="Arrays 1", category="Arrays")
    create_sample_file(temp_repo, "Arrays/P5.cpp", title="Arrays 2", category="Arrays")

    home_stats = backend.get_dashboard_stats(temp_repo)
    math_cat_view = backend.get_category_view(temp_repo, "Math")
    arrays_cat_view = backend.get_category_view(temp_repo, "Arrays")

    assert home_stats["category_counts"]["Math"] == math_cat_view["problem_count"] == 3
    assert home_stats["category_counts"]["Arrays"] == arrays_cat_view["problem_count"] == 2


def test_search_category_results_match_category_view(temp_repo):
    """16. Search category results match Category View problem count and records."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="Compound Interest", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P2.cpp", title="Mean Median Mode", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P3.cpp", title="Number Distribution", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P4.cpp", title="ODD and EVEN sum", category="Math", platform="Smart Interview")
    create_sample_file(temp_repo, "Math/P5.cpp", title="Triangle Validator", category="Math", platform="LeetCode")
    create_sample_file(temp_repo, "Arrays/P6.cpp", title="Two Sum", category="Arrays", platform="LeetCode")

    search_res = backend.search_problems(temp_repo, category="Math")
    cat_view = backend.get_category_view(temp_repo, "Math")

    assert search_res["total_matching"] == cat_view["problem_count"] == 5
    search_titles = [r["title"] for r in search_res["results"]]
    cat_titles = [p["title"] for p in cat_view["problems"]]
    assert set(search_titles) == set(cat_titles)


def test_add_problem_refreshes_category_view(temp_repo):
    """17. Adding a problem dynamically updates Category View data."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="Math 1", category="Math")
    res_before = backend.get_category_view(temp_repo, "Math")
    assert res_before["problem_count"] == 1

    create_sample_file(temp_repo, "Math/P2.cpp", title="Math 2", category="Math")
    res_after = backend.get_category_view(temp_repo, "Math")
    assert res_after["problem_count"] == 2
    assert len(res_after["problems"]) == 2


def test_rescan_refreshes_category_view(temp_repo):
    """18. Rescan discovers external filesystem changes and updates Category View."""
    create_sample_file(temp_repo, "Math/P1.cpp", title="Math 1", category="Math")
    assert backend.get_category_view(temp_repo, "Math")["problem_count"] == 1

    # Add file externally directly on disk
    create_sample_file(temp_repo, "Math/P2.cpp", title="Math 2", category="Math")
    scan_res = backend.scan_repository(temp_repo)
    assert scan_res["success"] is True

    cat_view = backend.get_category_view(temp_repo, "Math")
    assert cat_view["problem_count"] == 2
