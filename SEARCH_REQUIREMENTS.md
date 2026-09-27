# Search Migration Specifications & Requirements

This document defines the functional and architectural requirements for migrating the Search feature to React.

## 1. Core Principles
* **Metadata-Only Search Scope**:
  * Search matches **MUST** be derived exclusively from structured metadata fields.
  * **STRICT ISOLATION**: Do **NOT** search the solution-code body for tags, keywords, or queries. Implementation code (C++, Java, Python code lines) must remain isolated from search indexing.
* **Structured Tag Filtering**:
  * Tags such as `Tricky`, `Revision`, `Interview`, `Important`, and custom tags must be fully searchable and filterable from structured metadata.
  * Must support both full-text metadata matching and explicit filter dropdown / token selection.
  * Must adhere to metadata value normalization (case/whitespace deduplication).

## 2. Supported Search & Filter Dimensions
Search must support querying and multi-dimensional filtering across:
1. **Title**: Problem title.
2. **Platform**: e.g., LeetCode, Codeforces, Smart Interview (normalized).
3. **Primary Category**: e.g., Arrays, Math, Graphs, Dynamic Programming.
4. **Programming Language**: C++, Java, Python.
5. **Tags**: Structured tags (`Tricky`, `Revision`, `Interview`, `Important`, etc.).
6. **Concepts / Techniques**: e.g., Two Pointers, Binary Search, Sliding Window.
7. **Data Structures**: e.g., Monotonic Stack, Trie, Segment Tree.
8. **Importance**: Rating 1 to 5.

## 3. Backend & Bridge Contract
* When migrating Search to React:
  * Expose `search_problems` via `bridge/bridge_server.py` and `frontend/src/bridge.ts`.
  * Leverage `engine.backend.search_problems(repo_path, query, category, platform, language, tags, importance)`.
  * Ensure the existing test suite (`test_search.py`) remains the single source of functional truth.

## 4. Phase Boundary
* The legacy Tkinter Search UI must **NOT** be modified in this phase.
* Migration of Search UI to React will be implemented as its own dedicated phase.
