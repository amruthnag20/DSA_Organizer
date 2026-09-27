"""
test_home.py - Automated test suite for Phase 5A: Home Dashboard.

Tests verify:
1. Basic counts (empty repo, single problem, multiple problems, multi-language, ignore unrelated files).
2. Date statistics (this week, previous week, this month, previous month, Monday-Sunday boundary, calendar month boundary).
3. Streaks (single day, consecutive days, gaps, multi-problem single day, today active, yesterday active, longest streak).
4. Categories (Primary category counts, tags/concepts isolation, deterministic sorting, most practiced top 3, less practiced).
5. Recent problems (newest first, metadata integrity, missing date handling).
6. Incomplete metadata resilience (missing category, missing date, malformed file).
7. Integration & UI Refresh (create problem updates stats, rescan updates stats).
"""

from datetime import date, timedelta
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


# Helper to create a problem file directly on disk with specified metadata
def create_sample_file(
    repo_dir: Path,
    rel_path: str,
    title: str = "Two Sum",
    platform: str = "LeetCode",
    language: str = "C++",
    category: str = "Arrays",
    added_date: str = "2026-09-26",
    tags: str = "Interview, Must-Do",
    concepts: str = "Two Pointers, Hash Map",
    data_structures: str = "Array, Hash Table",
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
# 1. BASIC COUNTS
# ==============================================================================

def test_empty_repository_dashboard_stats(temp_repo):
    """1. Empty repository returns 0 for all counts and empty lists."""
    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["success"] is True
    assert stats["total_problems"] == 0
    assert stats["this_week"] == 0
    assert stats["this_month"] == 0
    assert stats["current_streak"] == 0
    assert stats["longest_streak"] == 0
    assert stats["category_counts"] == {}
    assert stats["most_practiced_categories"] == []
    assert stats["least_practiced_categories"] == []
    assert stats["recent_problems"] == []
    assert stats["activity_by_date"] == {}
    assert len(stats["heatmap_weeks"]) == 12


def test_single_problem_count(temp_repo):
    """2. Single valid problem results in total_problems = 1."""
    create_sample_file(temp_repo, "Arrays/TwoSum.cpp", title="Two Sum", category="Arrays", added_date="2026-09-26")
    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["total_problems"] == 1
    assert stats["category_counts"] == {"Arrays": 1}


def test_multiple_problems_count(temp_repo):
    """3. Multiple problems across categories produce correct total count."""
    create_sample_file(temp_repo, "Arrays/TwoSum.cpp", title="Two Sum", category="Arrays")
    create_sample_file(temp_repo, "Strings/ValidAnagram.cpp", title="Valid Anagram", category="Strings")
    create_sample_file(temp_repo, "Trees/Inorder.cpp", title="Inorder", category="Trees")
    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["total_problems"] == 3


def test_supported_languages_counted(temp_repo):
    """4. Supported languages .cpp, .java, and .py are recognized and counted."""
    create_sample_file(temp_repo, "Arrays/TwoSum.cpp", title="Two Sum", language="C++")
    create_sample_file(temp_repo, "Strings/ValidAnagram.java", title="Valid Anagram", language="Java")
    create_sample_file(temp_repo, "Trees/Inorder.py", title="Inorder", language="Python")
    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["total_problems"] == 3


def test_unrelated_files_ignored(temp_repo):
    """5. .git folder, txt, md, and build artifacts are not counted."""
    create_sample_file(temp_repo, "Arrays/TwoSum.cpp", title="Two Sum")
    (temp_repo / "README.md").write_text("# DSA Notes", encoding="utf-8")
    (temp_repo / "notes.txt").write_text("TODO", encoding="utf-8")
    git_dir = temp_repo / ".git"
    git_dir.mkdir()
    (git_dir / "config.cpp").write_text("// not a problem", encoding="utf-8")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["total_problems"] == 1


# ==============================================================================
# 2. DATE STATISTICS & BOUNDARIES
# ==============================================================================

def test_this_week_count(temp_repo):
    """6. Count problems added within the current calendar week."""
    # 2026-09-26 is Saturday. Week is Monday Sep 21 to Sunday Sep 27.
    today = date(2026, 9, 26)
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-21")  # Monday (in)
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", added_date="2026-09-24")  # Thursday (in)
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", added_date="2026-09-26")  # Saturday (in)
    create_sample_file(temp_repo, "Arrays/P4.cpp", title="P4", added_date="2026-09-27")  # Sunday (in)

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["this_week"] == 4
    assert stats["total_problems"] == 4


def test_previous_week_excluded_from_this_week(temp_repo):
    """7. Problems added in previous week are excluded from this_week."""
    today = date(2026, 9, 26)
    # Sunday Sep 20 is previous week
    create_sample_file(temp_repo, "Arrays/Old.cpp", title="Old", added_date="2026-09-20")
    create_sample_file(temp_repo, "Arrays/New.cpp", title="New", added_date="2026-09-22")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["total_problems"] == 2
    assert stats["this_week"] == 1


def test_this_month_count(temp_repo):
    """8. Count problems added in the current calendar month."""
    today = date(2026, 9, 26)
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-01")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", added_date="2026-09-15")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", added_date="2026-09-26")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["this_month"] == 3


def test_previous_month_excluded_from_this_month(temp_repo):
    """9. Problems from prior months are excluded from this_month."""
    today = date(2026, 9, 26)
    create_sample_file(temp_repo, "Arrays/Aug.cpp", title="Aug", added_date="2026-08-31")
    create_sample_file(temp_repo, "Arrays/Sep.cpp", title="Sep", added_date="2026-09-01")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["total_problems"] == 2
    assert stats["this_month"] == 1


def test_calendar_month_boundary(temp_repo):
    """10. Exact boundary between months (last day of month vs first day of next)."""
    today = date(2026, 10, 1)  # October 1
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-30")  # September
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", added_date="2026-10-01")  # October

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["total_problems"] == 2
    assert stats["this_month"] == 1  # Only P2


def test_monday_sunday_week_boundary(temp_repo):
    """11. Exact Monday to Sunday week boundaries."""
    # Week: Mon 2026-09-21 to Sun 2026-09-27
    today = date(2026, 9, 23)  # Wednesday
    create_sample_file(temp_repo, "Arrays/SundayPrior.cpp", title="Prior", added_date="2026-09-20")  # Sun prior (out)
    create_sample_file(temp_repo, "Arrays/MondayStart.cpp", title="Mon", added_date="2026-09-21")  # Mon (in)
    create_sample_file(temp_repo, "Arrays/SundayEnd.cpp", title="Sun", added_date="2026-09-27")    # Sun (in)
    create_sample_file(temp_repo, "Arrays/MondayNext.cpp", title="Next", added_date="2026-09-28")   # Mon next (out)

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["total_problems"] == 4
    assert stats["this_week"] == 2


# ==============================================================================
# 3. STREAKS
# ==============================================================================

def test_single_active_day_streak(temp_repo):
    """12. One active day on today gives current streak 1, longest streak 1."""
    today = date(2026, 9, 26)
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-26")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["current_streak"] == 1
    assert stats["longest_streak"] == 1


def test_consecutive_active_days_streak(temp_repo):
    """13. Consecutive active days ending today gives correct current and longest streak."""
    today = date(2026, 9, 26)
    for i in range(5):
        d_str = (today - timedelta(days=i)).isoformat()
        create_sample_file(temp_repo, f"Arrays/P{i}.cpp", title=f"P{i}", added_date=d_str)

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["current_streak"] == 5
    assert stats["longest_streak"] == 5


def test_gap_breaks_current_streak(temp_repo):
    """14. A missing day in streak breaks the current streak."""
    today = date(2026, 9, 26)
    # Active: Sep 26 (today), Sep 25, (Sep 24 gap), Sep 23, Sep 22, Sep 21
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-26")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", added_date="2026-09-25")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", added_date="2026-09-23")
    create_sample_file(temp_repo, "Arrays/P4.cpp", title="P4", added_date="2026-09-22")
    create_sample_file(temp_repo, "Arrays/P5.cpp", title="P5", added_date="2026-09-21")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["current_streak"] == 2
    assert stats["longest_streak"] == 3  # Sep 21-23


def test_multiple_problems_same_day_counts_as_one_active_day(temp_repo):
    """15. Multiple problems on a single day contribute only 1 active day."""
    today = date(2026, 9, 26)
    for i in range(10):
        create_sample_file(temp_repo, f"Arrays/P{i}.cpp", title=f"P{i}", added_date="2026-09-26")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["total_problems"] == 10
    assert stats["current_streak"] == 1
    assert stats["longest_streak"] == 1


def test_current_streak_today_active(temp_repo):
    """16. Current streak counts backwards starting from today when today is active."""
    today = date(2026, 9, 26)
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-26")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", added_date="2026-09-25")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", added_date="2026-09-24")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["current_streak"] == 3


def test_current_streak_today_inactive_yesterday_active(temp_repo):
    """17. If today is inactive but yesterday is active, streak counts through yesterday."""
    today = date(2026, 9, 26)
    # Today Sep 26 inactive, Sep 25 active, Sep 24 active
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-25")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", added_date="2026-09-24")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["current_streak"] == 2
    assert stats["longest_streak"] == 2


def test_current_streak_neither_today_nor_yesterday(temp_repo):
    """17b. If neither today nor yesterday is active, current streak is 0."""
    today = date(2026, 9, 26)
    # Active on Sep 24 (2 days ago)
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-24")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["current_streak"] == 0
    assert stats["longest_streak"] == 1


def test_longest_streak_across_multiple_periods(temp_repo):
    """18. Longest streak is the maximum consecutive sequence across all history."""
    today = date(2026, 9, 26)
    # Period 1: Sep 1, 2, 3, 4, 5 (5 days)
    for d in range(1, 6):
        create_sample_file(temp_repo, f"Arrays/Sep{d}.cpp", title=f"Sep{d}", added_date=f"2026-09-0{d}")
    # Period 2: Sep 25, 26 (2 days - current)
    create_sample_file(temp_repo, "Arrays/Sep25.cpp", title="Sep25", added_date="2026-09-25")
    create_sample_file(temp_repo, "Arrays/Sep26.cpp", title="Sep26", added_date="2026-09-26")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    assert stats["current_streak"] == 2
    assert stats["longest_streak"] == 5


# ==============================================================================
# 4. CATEGORIES
# ==============================================================================

def test_category_counts(temp_repo):
    """19. Primary Category counts are accurately grouped."""
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", category="Arrays")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", category="Arrays")
    create_sample_file(temp_repo, "Strings/P3.cpp", title="P3", category="Strings")
    create_sample_file(temp_repo, "Hashing/P4.cpp", title="P4", category="Hashing")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["category_counts"] == {"Arrays": 2, "Strings": 1, "Hashing": 1}


def test_tags_do_not_affect_category_counts(temp_repo):
    """20. Tags like 'Arrays', 'Strings' do not get confused with Primary Category."""
    create_sample_file(
        temp_repo,
        "DynamicProgramming/CoinChange.cpp",
        title="Coin Change",
        category="DynamicProgramming",
        tags="Arrays, Trees, Hashing",
    )
    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["category_counts"] == {"DynamicProgramming": 1}
    assert "Arrays" not in stats["category_counts"]


def test_concepts_do_not_affect_category_counts(temp_repo):
    """21. Concepts/Techniques do not get counted as Primary Categories."""
    create_sample_file(
        temp_repo,
        "Graphs/Dijkstra.cpp",
        title="Dijkstra",
        category="Graphs",
        concepts="Greedy, Heaps, Shortest Path",
    )
    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["category_counts"] == {"Graphs": 1}
    assert "Greedy" not in stats["category_counts"]


def test_deterministic_category_sorting(temp_repo):
    """22. Categories are sorted by count descending, then alphabetically."""
    create_sample_file(temp_repo, "Trees/P1.cpp", title="P1", category="Trees")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", category="Arrays")
    create_sample_file(temp_repo, "Graphs/P3.cpp", title="P3", category="Graphs")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    # All count 1, so tie-breaker is alphabetical: Arrays, Graphs, Trees
    expected = [("Arrays", 1), ("Graphs", 1), ("Trees", 1)]
    assert stats["most_practiced_categories"] == expected


def test_most_practiced_top_three(temp_repo):
    """23. Most practiced displays top 3 categories."""
    for i in range(5):
        create_sample_file(temp_repo, f"Arrays/A{i}.cpp", title=f"A{i}", category="Arrays")
    for i in range(4):
        create_sample_file(temp_repo, f"Strings/S{i}.cpp", title=f"S{i}", category="Strings")
    for i in range(3):
        create_sample_file(temp_repo, f"Hashing/H{i}.cpp", title=f"H{i}", category="Hashing")
    for i in range(2):
        create_sample_file(temp_repo, f"Trees/T{i}.cpp", title=f"T{i}", category="Trees")
    for i in range(1):
        create_sample_file(temp_repo, f"Graphs/G{i}.cpp", title=f"G{i}", category="Graphs")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["most_practiced_categories"] == [("Arrays", 5), ("Strings", 4), ("Hashing", 3)]


def test_less_practiced_categories(temp_repo):
    """24. Less practiced displays lowest 3 categories."""
    for i in range(5):
        create_sample_file(temp_repo, f"Arrays/A{i}.cpp", title=f"A{i}", category="Arrays")
    for i in range(4):
        create_sample_file(temp_repo, f"Strings/S{i}.cpp", title=f"S{i}", category="Strings")
    for i in range(3):
        create_sample_file(temp_repo, f"Hashing/H{i}.cpp", title=f"H{i}", category="Hashing")
    for i in range(2):
        create_sample_file(temp_repo, f"Trees/T{i}.cpp", title=f"T{i}", category="Trees")
    for i in range(1):
        create_sample_file(temp_repo, f"Graphs/G{i}.cpp", title=f"G{i}", category="Graphs")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    # Least practiced sorted by lowest count: Graphs (1), Trees (2), Hashing (3)
    assert stats["least_practiced_categories"] == [("Graphs", 1), ("Trees", 2), ("Hashing", 3)]


def test_fewer_than_three_categories(temp_repo):
    """24b. If fewer than 3 categories exist, display available categories without padding."""
    create_sample_file(temp_repo, "Arrays/A1.cpp", title="A1", category="Arrays")
    create_sample_file(temp_repo, "Strings/S1.cpp", title="S1", category="Strings")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert len(stats["most_practiced_categories"]) == 2
    assert len(stats["least_practiced_categories"]) == 2


# ==============================================================================
# 5. RECENT PROBLEMS
# ==============================================================================

def test_recent_problems_newest_first_ordering(temp_repo):
    """25. Recent problems are ordered newest Added date first."""
    create_sample_file(temp_repo, "Arrays/Old.cpp", title="Old Problem", added_date="2026-09-01")
    create_sample_file(temp_repo, "Arrays/Mid.cpp", title="Mid Problem", added_date="2026-09-15")
    create_sample_file(temp_repo, "Arrays/New.cpp", title="New Problem", added_date="2026-09-26")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    recent = stats["recent_problems"]
    assert len(recent) == 3
    assert recent[0]["title"] == "New Problem"
    assert recent[1]["title"] == "Mid Problem"
    assert recent[2]["title"] == "Old Problem"


def test_recent_problems_metadata_fields(temp_repo):
    """26. Recent problems include title, category, platform, language, and formatted date."""
    create_sample_file(
        temp_repo,
        "Arrays/TwoSum.cpp",
        title="Two Sum",
        platform="LeetCode",
        language="C++",
        category="Arrays",
        added_date="2026-09-26",
    )
    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    recent = stats["recent_problems"]
    assert len(recent) == 1
    p = recent[0]
    assert p["title"] == "Two Sum"
    assert p["category"] == "Arrays"
    assert p["platform"] == "LeetCode"
    assert p["language"] == "C++"
    assert p["added_date"] == "2026-09-26"
    assert "September 26, 2026" in p["formatted_date"]


def test_recent_problems_missing_added_date_not_assigned_fake_date(temp_repo):
    """27. Problem missing Added date does not get assigned today's date."""
    # Create file with no Added date
    raw_content = """/**
 * Problem: No Date Problem
 * Platform: LeetCode
 * Language: C++
 * Primary Category: Arrays
 */
int main() { return 0; }
"""
    f = temp_repo / "Arrays" / "NoDate.cpp"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(raw_content, encoding="utf-8")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["total_problems"] == 1
    # Should not contribute to this_week, this_month, or streak
    assert stats["this_week"] == 0
    assert stats["this_month"] == 0
    assert stats["current_streak"] == 0
    assert stats["longest_streak"] == 0

    recent = stats["recent_problems"]
    assert len(recent) == 1
    assert recent[0]["parsed_date"] is None
    assert recent[0]["added_date"] == ""


# ==============================================================================
# 6. INCOMPLETE & MALFORMED METADATA RESILIENCE
# ==============================================================================

def test_missing_category_does_not_crash_dashboard(temp_repo):
    """28. Problem missing Primary Category contributes to total_problems without crashing."""
    raw_content = """/**
 * Problem: Missing Category
 * Platform: LeetCode
 * Language: C++
 * Added: 2026-09-26
 */
int main() { return 0; }
"""
    f = temp_repo / "Misc" / "NoCat.cpp"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(raw_content, encoding="utf-8")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["total_problems"] == 1
    assert stats["this_week"] == 1
    assert stats["current_streak"] == 1
    assert stats["category_counts"] == {}


def test_missing_date_does_not_crash_dashboard(temp_repo):
    """29. Missing Added date does not crash streak or date calculations."""
    raw_content = """/**
 * Problem: Missing Date
 * Platform: LeetCode
 * Language: C++
 * Primary Category: Strings
 */
int main() { return 0; }
"""
    f = temp_repo / "Strings" / "NoDate.cpp"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(raw_content, encoding="utf-8")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["total_problems"] == 1
    assert stats["category_counts"] == {"Strings": 1}
    assert stats["current_streak"] == 0


def test_malformed_unreadable_file_does_not_crash_dashboard(temp_repo):
    """30. A raw unreadable source file without headers does not crash dashboard."""
    f = temp_repo / "Raw" / "RawCode.cpp"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("#include <iostream>\nint main() { return 0; }", encoding="utf-8")

    stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))
    assert stats["total_problems"] == 1
    assert stats["this_week"] == 0
    assert stats["current_streak"] == 0
    assert len(stats["recent_problems"]) == 1


# ==============================================================================
# 7. INTEGRATION & ACTIVITY HEATMAP
# ==============================================================================

def test_heatmap_structure_and_intensity(temp_repo):
    """Activity heatmap correctly populates 12 weeks of data and levels."""
    today = date(2026, 9, 26)
    create_sample_file(temp_repo, "Arrays/P1.cpp", title="P1", added_date="2026-09-26")
    create_sample_file(temp_repo, "Arrays/P2.cpp", title="P2", added_date="2026-09-26")
    create_sample_file(temp_repo, "Arrays/P3.cpp", title="P3", added_date="2026-09-25")

    stats = backend.get_dashboard_stats(temp_repo, today=today)
    weeks = stats["heatmap_weeks"]
    assert len(weeks) == 12
    for w in weeks:
        assert len(w) == 7

    # Find today's cell in the last week
    today_cells = [cell for week in weeks for cell in week if cell["date"] == "2026-09-26"]
    assert len(today_cells) == 1
    assert today_cells[0]["count"] == 2
    assert today_cells[0]["level"] == 2
    assert today_cells[0]["is_today"] is True

    # Find yesterday's cell
    yesterday_cells = [cell for week in weeks for cell in week if cell["date"] == "2026-09-25"]
    assert len(yesterday_cells) == 1
    assert yesterday_cells[0]["count"] == 1
    assert yesterday_cells[0]["level"] == 1


def test_integration_add_problem_updates_dashboard_stats(temp_repo, temp_config):
    """31. After creating a new problem via backend, refreshed stats immediately reflect it."""
    today_actual = date.today()
    # 1. Initial dashboard stats on empty repo
    initial_stats = backend.get_dashboard_stats(temp_repo, today=today_actual)
    assert initial_stats["total_problems"] == 0

    # 2. Add problem using create_problem_file
    backend.save_repository_config(str(temp_repo))
    ok, msg, f_path = backend.create_problem_file(
        repo_path=str(temp_repo),
        title="Climbing Stairs",
        platform="LeetCode",
        language="C++",
        category="DynamicProgramming",
        description="Ways to climb n stairs.",
        solution_code="int climbStairs(int n) { return n; }",
    )
    assert ok is True

    # 3. Re-calculate dashboard stats
    refreshed_stats = backend.get_dashboard_stats(temp_repo, today=today_actual)
    assert refreshed_stats["total_problems"] == 1
    assert refreshed_stats["this_week"] == 1
    assert refreshed_stats["this_month"] == 1
    assert refreshed_stats["current_streak"] == 1
    assert refreshed_stats["category_counts"] == {"DynamicProgramming": 1}
    assert refreshed_stats["recent_problems"][0]["title"] == "Climbing Stairs"


def test_integration_rescan_refreshes_dashboard_stats(temp_repo):
    """32. Rescan and get_dashboard_stats return consistent data."""
    create_sample_file(temp_repo, "Arrays/TwoSum.cpp", title="Two Sum", category="Arrays", added_date="2026-09-26")
    scan_res = backend.scan_repository(temp_repo)
    dash_stats = backend.get_dashboard_stats(temp_repo, today=date(2026, 9, 26))

    assert scan_res["total_problems"] == dash_stats["total_problems"]
    assert len(scan_res["problems"]) == len(dash_stats["problems"])


def test_ui_home_is_first_screen_when_repo_configured(temp_repo, temp_config):
    """Home screen is displayed first when repository is configured."""
    import tkinter as tk
    from main import DSAOrganizerApp

    backend.save_repository_config(str(temp_repo))
    create_sample_file(temp_repo, "Arrays/TwoSum.cpp", title="Two Sum", category="Arrays")

    root = tk.Tk()
    root.withdraw()
    try:
        app = DSAOrganizerApp(root)
        root.update()
        assert app._current_view == "home"
        assert app.stat_total_var.get() == "1"
    finally:
        root.destroy()


def test_ui_shows_repo_view_when_no_repo_configured(temp_config):
    """Repo configuration screen is displayed when no repository is configured."""
    import tkinter as tk
    from main import DSAOrganizerApp

    root = tk.Tk()
    root.withdraw()
    try:
        app = DSAOrganizerApp(root)
        root.update()
        assert app._current_view == "repo"
    finally:
        root.destroy()


def test_ui_view_switching(temp_repo, temp_config):
    """Toggling between Home and Repo views switches correctly."""
    import tkinter as tk
    from main import DSAOrganizerApp

    backend.save_repository_config(str(temp_repo))

    root = tk.Tk()
    root.withdraw()
    try:
        app = DSAOrganizerApp(root)
        root.update()
        assert app._current_view == "home"

        app._show_view("repo")
        root.update()
        assert app._current_view == "repo"

        app._show_view("home")
        root.update()
        assert app._current_view == "home"
    finally:
        root.destroy()


def test_ui_refreshes_after_problem_created(temp_repo, temp_config):
    """Creating a problem updates the UI statistics directly."""
    import tkinter as tk
    from main import DSAOrganizerApp

    backend.save_repository_config(str(temp_repo))

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment")
    root.withdraw()
    try:
        app = DSAOrganizerApp(root)
        root.update()
        assert app.stat_total_var.get() == "0"

        # Create problem
        ok, msg, fpath = backend.create_problem_file(
            repo_path=str(temp_repo),
            title="Binary Search",
            platform="LeetCode",
            language="C++",
            category="Searching",
            description="Binary search in sorted array.",
            solution_code="int search() { return 0; }",
        )
        assert ok is True

        # Trigger callback as AddProblemDialog would
        app._on_problem_created(fpath, "Binary Search", "Searching")
        root.update()

        assert app.stat_total_var.get() == "1"
        assert app.stat_week_var.get() == "1"
        assert app.stat_month_var.get() == "1"
        assert app.stat_streak_var.get() == "1 day"
    finally:
        root.destroy()

