"""
backend.py - Core engine logic for DSA Organizer (Phase 0, Phase 1, Phase 1.5, Phase 2).

Phase 0:
- Ensuring core project directories exist (engine/, DSA/)
- Loading configuration from project.json safely
- Validating repository paths via physical filesystem checks
- Saving repository configuration with read-back verification
- Handling configuration errors and malformed files safely

Phase 1:
- Supported languages, extensions, platforms, and primary categories
- Problem title sanitization and PascalCase filename generation
- Path safety and directory traversal prevention
- Standardized metadata header formatting per language
- File creation in the configured repository under the resolved category folder
- Duplicate file prevention
- Physical file verification (existence, is_file, and read-back content match)

Phase 1.5 additions:
- User-provided metadata: Concepts / Techniques, Data Structures
- Engine-determined complexity analysis: Time Complexity, Space Complexity
- Updated source file header embedding complexity and new user metadata

Phase 2 additions:
- Git availability detection (is_git_available)
- Git repository verification (is_git_repository)
- Git status retrieval (get_git_status)
- Single-file staging, never staging unrelated files (git_add_file)
- User-triggered commit with explicit message (git_commit)
- Push to configured remote (git_push)
- Safety: no shell=True, no credential handling, no automatic operations
"""

from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple, Set

try:
    from engine.complexity import analyze_complexity
except ImportError:
    from complexity import analyze_complexity

# Supported languages and extension mapping
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "C++": ".cpp",
    "Java": ".java",
    "Python": ".py",
}

BUILTIN_PLATFORMS: List[str] = [
    "LeetCode",
    "CodeChef",
    "HackerRank",
    "Codeforces",
    "GeeksForGeeks",
]

# Standard platforms (built-ins + Other)
SUPPORTED_PLATFORMS: List[str] = BUILTIN_PLATFORMS + ["Other"]

# Built-in reusable tags
BUILTIN_TAGS: List[str] = [
    "Interview",
    "Important",
    "Revision",
    "Tricky",
    "Must-Do",
    "Pattern",
]

# Standard deterministic DSA primary categories
DEFAULT_CATEGORIES: List[str] = [
    "Arrays",
    "Strings",
    "LinkedLists",
    "Stacks",
    "Queues",
    "Hashing",
    "Trees",
    "Graphs",
    "Heaps",
    "Recursion",
    "Backtracking",
    "Sorting",
    "Searching",
    "Greedy",
    "DynamicProgramming",
    "Uncategorized",
]

# Standard canonical concepts / techniques
BUILTIN_CONCEPTS: List[str] = [
    "Two Pointer",
    "Sliding Window",
    "Binary Search",
    "Depth-First Search",
    "Breadth-First Search",
    "Dynamic Programming",
    "Greedy",
    "Backtracking",
    "Bit Manipulation",
    "Divide and Conquer",
    "Recursion",
    "Prefix Sum",
    "Math",
]

# Standard canonical data structures
BUILTIN_DATA_STRUCTURES: List[str] = [
    "Array",
    "String",
    "Linked List",
    "Stack",
    "Queue",
    "HashMap",
    "HashSet",
    "Binary Tree",
    "Binary Search Tree",
    "Heap",
    "Graph",
    "Trie",
    "Matrix",
]



def get_project_root() -> Path:
    """Return the absolute Path to the DSAORGANIZER root directory."""
    return Path(__file__).resolve().parent.parent


def get_config_path() -> Path:
    """Return the Path to project.json in the project root."""
    return get_project_root() / "project.json"


def ensure_project_directories() -> Tuple[bool, str]:
    """
    Ensure the mandatory base directories (engine/ and DSA/) exist physically.
    Does NOT create any category folders or solution files.
    """
    root = get_project_root()
    engine_dir = root / "engine"
    dsa_dir = root / "DSA"

    try:
        engine_dir.mkdir(parents=True, exist_ok=True)
        dsa_dir.mkdir(parents=True, exist_ok=True)

        if not engine_dir.is_dir():
            return False, f"engine directory missing or not a directory: {engine_dir}"
        if not dsa_dir.is_dir():
            return False, f"DSA directory missing or not a directory: {dsa_dir}"

        return True, "Core directories verified."
    except Exception as exc:
        return False, f"Failed to ensure project directories: {exc}"


def validate_repository(repo_path: Optional[str | Path]) -> Tuple[bool, str]:
    """
    Validate whether the specified path is a valid, accessible directory.

    Returns:
        (is_valid, status_message)
    """
    if not repo_path or str(repo_path).strip() == "":
        return False, "No repository configured."

    target = Path(repo_path).resolve()

    if not target.exists():
        return False, f"Repository path does not exist: {target}"

    if not target.is_dir():
        return False, f"Selected path is not a directory: {target}"

    # Verify directory read access
    try:
        os.listdir(target)
    except PermissionError:
        return False, f"Permission denied accessing directory: {target}"
    except Exception as exc:
        return False, f"Unable to access directory: {exc}"

    return True, "Repository found"


def load_config() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Load project configuration from project.json.
    If project.json does not exist, creates it with safe defaults.

    Returns:
        (config_dict, error_message)
        If an error occurred (e.g. malformed JSON), config_dict is None and error_message is populated.
    """
    config_file = get_config_path()

    if not config_file.exists():
        default_config: Dict[str, Any] = {
            "repository": "",
            "default_language": "cpp",
        }
        success, msg = _write_and_verify_json(config_file, default_config)
        if not success:
            return None, f"Failed to create default configuration: {msg}"
        return default_config, None

    if not config_file.is_file():
        return None, f"Configuration path is not a file: {config_file}"

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return None, "Configuration file is invalid: root element must be a JSON object."

        return data, None
    except json.JSONDecodeError as err:
        return None, f"Configuration file is malformed (JSON parse error): {err}"
    except Exception as exc:
        return None, f"Unable to read configuration file: {exc}"


def _write_and_verify_json(file_path: Path, data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Write data to JSON file and physically verify write by reading it back.
    """
    try:
        temp_path = file_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())

        # Replace destination atomically on Windows
        os.replace(temp_path, file_path)

        if not file_path.exists():
            return False, f"File {file_path} was not created on disk."

        # Physical read-back verification
        with open(file_path, "r", encoding="utf-8") as f:
            verified_data = json.load(f)

        if verified_data != data:
            return False, "Verification failed: Read-back configuration does not match data written."

        return True, "Saved and verified successfully."
    except Exception as exc:
        return False, f"Filesystem write failed: {exc}"


def save_repository_config(repo_path: str | Path, remote_url: Optional[str] = None) -> Tuple[bool, str]:
    """
    Save the repository path (and optional Git remote URL) to project.json
    after validating the path and verifying the updated configuration can be read back from disk.

    Returns:
        (success, message)
    """
    # 1. Validate the path
    is_valid, validation_msg = validate_repository(repo_path)
    if not is_valid:
        return False, validation_msg

    resolved_path_str = str(Path(repo_path).resolve())

    # 2. Check existing configuration to avoid overwriting a malformed file silently
    config, load_err = load_config()
    if load_err:
        return False, f"Cannot save configuration: {load_err}\nPlease inspect project.json before modifying."

    if config is None:
        config = {"default_language": "cpp"}

    config["repository"] = resolved_path_str
    config["repository_path"] = resolved_path_str

    if remote_url is not None:
        clean_remote = remote_url.strip()
        if clean_remote:
            if "git" not in config or not isinstance(config["git"], dict):
                config["git"] = {}
            config["git"]["remote_name"] = "origin"
            config["git"]["remote_url"] = clean_remote
        elif "git" in config and isinstance(config["git"], dict) and "remote_url" in config["git"]:
            # If user explicitly cleared remote url
            config["git"]["remote_url"] = ""

    # 3. Save to project.json and verify write
    config_file = get_config_path()
    write_ok, write_msg = _write_and_verify_json(config_file, config)
    if not write_ok:
        return False, f"Unable to save project configuration.\n{write_msg}"

    # 4. Reload configuration from disk to confirm persistence
    reloaded_config, reload_err = load_config()
    if reload_err or not reloaded_config:
        return False, f"Failed to reload saved configuration: {reload_err}"

    # 5. Confirm saved repository path matches selected path
    if reloaded_config.get("repository") != resolved_path_str and reloaded_config.get("repository_path") != resolved_path_str:
        return False, "Verification mismatch: Reloaded repository path does not match selected path."

    # 6. Only then report success
    return True, f"Repository configured successfully.\n\nPath:\n{resolved_path_str}\n\n✓ Configuration saved"


# ==============================================================================
# METADATA NORMALIZATION & CANONICAL DEDUPLICATION SYSTEM
# ==============================================================================

def normalize_metadata_key(value: Any) -> str:
    """
    Produce a deterministic lowercase, whitespace-collapsed identity key for comparison and deduplication.
    Example: '  Smart   Interview  ' -> 'smart interview'
    """
    if value is None:
        return ""
    val_str = str(value).strip()
    # Collapse multiple consecutive whitespace characters into a single space
    collapsed = re.sub(r"\s+", " ", val_str)
    return collapsed.lower()


def normalize_metadata_display(value: Any) -> str:
    """
    Trim outer whitespace and collapse repeated internal whitespace while preserving original casing.
    Example: '  Smart   Interview  ' -> 'Smart Interview'
    """
    if value is None:
        return ""
    val_str = str(value).strip()
    return re.sub(r"\s+", " ", val_str)


def build_canonical_mapping(
    configured_values: List[str],
    discovered_values: List[str],
) -> Dict[str, str]:
    """
    Build a mapping from normalized_identity_key -> canonical_display_value.

    Deterministic Preference Order:
    1. Configured / Built-in values (highest priority, in order given).
    2. Discovered repository values with the highest frequency.
    3. Alphabetical / lexicographical tie-breaker.
    """
    from collections import Counter

    canonical_map: Dict[str, str] = {}

    # 1. Configured / built-in values first
    for val in configured_values:
        clean_disp = normalize_metadata_display(val)
        norm_k = normalize_metadata_key(val)
        if norm_k and norm_k not in canonical_map:
            canonical_map[norm_k] = clean_disp

    # 2. Count frequencies of discovered values
    cleaned_discovered = [normalize_metadata_display(v) for v in discovered_values if str(v).strip()]
    freq_counts = Counter(cleaned_discovered)

    # Group discovered display values by normalized key
    grouped_by_norm: Dict[str, List[str]] = {}
    for disp_val in cleaned_discovered:
        norm_k = normalize_metadata_key(disp_val)
        if norm_k not in grouped_by_norm:
            grouped_by_norm[norm_k] = []
        grouped_by_norm[norm_k].append(disp_val)

    for norm_k, variants in grouped_by_norm.items():
        # Prefer: (-frequency, title_case_preference, case_insensitive_order)
        def variant_sort_key(v: str) -> Tuple[int, int, str]:
            is_title = 0 if (v.istitle() or (len(v) > 1 and v[0].isupper() and not v.isupper())) else 1
            return (-freq_counts[v], is_title, v.lower())

        unique_variants = sorted(list(set(variants)), key=variant_sort_key)
        best_discovered = unique_variants[0]
        if norm_k not in canonical_map:
            canonical_map[norm_k] = best_discovered
        else:
            curr = canonical_map[norm_k]
            if (curr.islower() or curr.isupper()) and not best_discovered.islower() and not best_discovered.isupper():
                canonical_map[norm_k] = best_discovered

    return canonical_map


def canonicalize_value(
    value: str,
    canonical_map: Optional[Dict[str, str]] = None,
    fallback_pool: Optional[List[str]] = None,
) -> str:
    """
    Given an input string (e.g. 'smart interview' or '  Revision '), return its canonical representation
    if a normalized match exists in canonical_map or fallback_pool; otherwise return cleaned display value.
    """
    clean_disp = normalize_metadata_display(value)
    norm_k = normalize_metadata_key(value)
    if not norm_k:
        return ""

    if canonical_map and norm_k in canonical_map:
        return canonical_map[norm_k]

    if fallback_pool:
        for item in fallback_pool:
            if normalize_metadata_key(item) == norm_k:
                return normalize_metadata_display(item)

    return clean_disp


def canonicalize_token_list(
    raw_tokens_str: str,
    canonical_map: Optional[Dict[str, str]] = None,
    fallback_pool: Optional[List[str]] = None,
) -> Tuple[List[str], str]:
    """
    Given a comma-separated string of tokens (e.g. 'interview, revision, TRICKY'),
    splits, canonicalizes each token, removes duplicates while preserving order,
    and returns (list_of_canonical_tokens, joined_comma_string).
    """
    if not raw_tokens_str:
        return [], ""

    raw_list = [t.strip() for t in raw_tokens_str.split(",") if t.strip()]
    seen_keys = set()
    canonical_tokens = []

    for t in raw_list:
        norm_k = normalize_metadata_key(t)
        if norm_k and norm_k not in seen_keys:
            seen_keys.add(norm_k)
            canon_val = canonicalize_value(t, canonical_map=canonical_map, fallback_pool=fallback_pool)
            canonical_tokens.append(canon_val)

    return canonical_tokens, ", ".join(canonical_tokens)


# ==============================================================================
# CUSTOM PLATFORM MANAGEMENT (PHASE 2)
# ==============================================================================

def get_custom_platforms() -> List[str]:
    """
    Return the list of saved custom platforms from project.json.
    """
    config, _ = load_config()
    if config and isinstance(config.get("platforms"), dict):
        custom = config["platforms"].get("custom", [])
        if isinstance(custom, list):
            # Deduplicate by normalized key while preserving display
            seen = set()
            result = []
            for p in custom:
                clean_p = normalize_metadata_display(p)
                norm_k = normalize_metadata_key(p)
                if norm_k and norm_k not in seen:
                    seen.add(norm_k)
                    result.append(clean_p)
            return result
    return []


def get_all_platforms() -> List[str]:
    """
    Return all platforms in order:
    Built-in platforms + Saved custom platforms + 'Other'
    """
    custom = get_custom_platforms()
    builtin_keys = {normalize_metadata_key(b) for b in BUILTIN_PLATFORMS}
    filtered_custom = [c for c in custom if normalize_metadata_key(c) not in builtin_keys and normalize_metadata_key(c) != "other"]
    return list(BUILTIN_PLATFORMS) + filtered_custom + ["Other"]


def save_custom_platform(name: str) -> Tuple[bool, str]:
    """
    Save a new custom platform into project.json:
    1. Validate that the name is not empty.
    2. Trim and collapse unnecessary whitespace.
    3. Check for duplicates using normalize_metadata_key against built-ins and saved custom platforms.
    4. Add to saved platform list.
    5. Persist in project.json.
    """
    clean_name = normalize_metadata_display(name)
    norm_k = normalize_metadata_key(name)
    if not norm_k:
        return False, "Platform name cannot be empty."

    # Check built-in platforms and "Other"
    for b in BUILTIN_PLATFORMS + ["Other"]:
        if norm_k == normalize_metadata_key(b):
            return False, f"'{clean_name}' is already a built-in platform (matches '{b}')."

    config, err = load_config()
    if err:
        return False, f"Failed to load configuration: {err}"
    if config is None:
        config = {"default_language": "cpp"}

    platforms_dict = config.setdefault("platforms", {})
    if not isinstance(platforms_dict, dict):
        platforms_dict = {}
        config["platforms"] = platforms_dict

    custom_list = platforms_dict.setdefault("custom", [])
    if not isinstance(custom_list, list):
        custom_list = []
        platforms_dict["custom"] = custom_list

    for c in custom_list:
        if normalize_metadata_key(c) == norm_k:
            return False, f"Platform '{clean_name}' is already saved (matches '{c}')."

    custom_list.append(clean_name)

    config_file = get_config_path()
    ok, msg = _write_and_verify_json(config_file, config)
    if not ok:
        return False, f"Failed to save custom platform: {msg}"

    return True, f"Platform '{clean_name}' saved successfully."


def delete_custom_platform(name: str) -> Tuple[bool, str]:
    """
    Remove a previously saved custom platform from project.json.
    """
    clean_name = normalize_metadata_display(name)
    norm_k = normalize_metadata_key(name)
    if not norm_k:
        return False, "Platform name cannot be empty."

    config, err = load_config()
    if err or not config:
        return False, f"Could not load configuration: {err}"

    platforms = config.get("platforms", {})
    if not isinstance(platforms, dict):
        return False, "No custom platforms configured."

    custom_list = platforms.get("custom", [])
    if not isinstance(custom_list, list):
        return False, "No custom platforms configured."

    orig_len = len(custom_list)
    new_list = [p for p in custom_list if normalize_metadata_key(p) != norm_k]

    if len(new_list) == orig_len:
        return False, f"Platform '{clean_name}' was not found in saved platforms."

    platforms["custom"] = new_list
    config_file = get_config_path()
    ok, msg = _write_and_verify_json(config_file, config)
    if not ok:
        return False, f"Failed to update configuration: {msg}"

    return True, f"Platform '{clean_name}' removed successfully."



# ==============================================================================
# CUSTOM CATEGORY MANAGEMENT (PHASE 2.5)
# ==============================================================================

# ==============================================================================
# CUSTOM CATEGORY MANAGEMENT (PHASE 2.5)
# ==============================================================================

def get_custom_categories() -> List[str]:
    """
    Return the list of saved custom primary categories from project.json.
    """
    config, _ = load_config()
    if config and isinstance(config.get("categories"), dict):
        custom = config["categories"].get("custom", [])
        if isinstance(custom, list):
            seen = set()
            result = []
            for c in custom:
                clean_c = normalize_metadata_display(c)
                norm_k = normalize_metadata_key(c)
                if norm_k and norm_k not in seen:
                    seen.add(norm_k)
                    result.append(clean_c)
            return result
    elif config and isinstance(config.get("categories"), list):
        # Backward compatibility for flat list configuration
        builtin_keys = {normalize_metadata_key(b) for b in DEFAULT_CATEGORIES}
        seen = set()
        result = []
        for c in config["categories"]:
            clean_c = normalize_metadata_display(c)
            norm_k = normalize_metadata_key(c)
            if norm_k and norm_k not in builtin_keys and norm_k not in seen:
                seen.add(norm_k)
                result.append(clean_c)
        return result
    return []


def get_categories() -> List[str]:
    """
    Return all primary categories in order:
    Built-in DEFAULT_CATEGORIES + Saved custom categories
    """
    builtin_keys = {normalize_metadata_key(b) for b in DEFAULT_CATEGORIES}
    custom = get_custom_categories()
    filtered_custom = [c for c in custom if normalize_metadata_key(c) not in builtin_keys]
    return list(DEFAULT_CATEGORIES) + filtered_custom


def validate_category_name(name: str) -> Tuple[bool, str]:
    """
    Validate a category name:
    - Must not be empty.
    - Path traversal ('..') and path separators ('/', '\\', ':') are rejected.
    - Invalid filesystem characters are rejected.
    - Case-insensitive / whitespace duplicate check against built-in and saved custom categories.

    Returns:
        (is_valid, error_or_clean_name)
    """
    clean_name = normalize_metadata_display(name)
    norm_k = normalize_metadata_key(name)
    if not norm_k:
        return False, "Category name cannot be empty."

    # Path traversal and path separator checks
    if ".." in clean_name:
        return False, "Unsafe category name: path traversal ('..') is not permitted."
    if "/" in clean_name or "\\" in clean_name or ":" in clean_name:
        return False, "Unsafe category name: path separators and drive specifiers are not permitted."

    # Invalid filesystem characters check
    invalid_chars = set(r'<>:"/\|?*')
    found_invalid = [ch for ch in clean_name if ch in invalid_chars]
    if found_invalid:
        return False, f"Category name contains invalid characters: {' '.join(found_invalid)}"

    # Check against built-in categories
    for b in DEFAULT_CATEGORIES:
        if norm_k == normalize_metadata_key(b):
            return False, f"'{clean_name}' is already a built-in category (matches '{b}')."

    # Check against saved custom categories
    saved = get_custom_categories()
    for s in saved:
        if norm_k == normalize_metadata_key(s):
            return False, f"Category '{clean_name}' is already saved (matches '{s}')."

    return True, clean_name


def save_custom_category(name: str) -> Tuple[bool, str]:
    """
    Validate and save a new custom category to project.json:
    - Name is validated and sanitized.
    - Duplicates and path traversal are rejected.
    - Persisted in project.json under 'categories.custom'.
    """
    is_valid, clean_or_err = validate_category_name(name)
    if not is_valid:
        return False, clean_or_err

    clean_name = clean_or_err
    norm_k = normalize_metadata_key(clean_name)

    config, err = load_config()
    if err:
        return False, f"Failed to load configuration: {err}"
    if config is None:
        config = {"default_language": "cpp"}

    cats_dict = config.setdefault("categories", {})
    if not isinstance(cats_dict, dict):
        cats_dict = {}
        config["categories"] = cats_dict

    custom_list = cats_dict.setdefault("custom", [])
    if not isinstance(custom_list, list):
        custom_list = []
        cats_dict["custom"] = custom_list

    for c in custom_list:
        if normalize_metadata_key(c) == norm_k:
            return False, f"Category '{clean_name}' is already saved (matches '{c}')."

    custom_list.append(clean_name)

    config_file = get_config_path()
    ok, msg = _write_and_verify_json(config_file, config)
    if not ok:
        return False, f"Failed to save custom category: {msg}"

    return True, f"Category '{clean_name}' saved successfully."


def delete_custom_category(name: str, repo_path: Optional[str | Path] = None) -> Tuple[bool, str]:
    """
    Remove a saved custom category from project.json.

    Safety Guarantee:
    - Never deletes user problems or directories containing user files.
    - If user files exist on disk inside the category folder, they remain untouched.
    """
    clean_name = normalize_metadata_display(name)
    norm_k = normalize_metadata_key(name)
    if not norm_k:
        return False, "Category name cannot be empty."

    for b in DEFAULT_CATEGORIES:
        if norm_k == normalize_metadata_key(b):
            return False, f"Cannot delete built-in category '{clean_name}'."

    config, err = load_config()
    if err or not config:
        return False, f"Could not load configuration: {err}"

    cats_dict = config.get("categories", {})
    if not isinstance(cats_dict, dict):
        return False, "No custom categories configured."

    custom_list = cats_dict.get("custom", [])
    if not isinstance(custom_list, list):
        return False, "No custom categories configured."

    matched = None
    for c in custom_list:
        if normalize_metadata_key(c) == norm_k:
            matched = str(c).strip()
            break

    if not matched:
        return False, f"Category '{clean_name}' is not in saved categories."

    # Remove from custom list in configuration
    new_list = [c for c in custom_list if normalize_metadata_key(c) != norm_k]
    cats_dict["custom"] = new_list

    config_file = get_config_path()
    ok, msg = _write_and_verify_json(config_file, config)
    if not ok:
        return False, f"Failed to update configuration: {msg}"

    return True, f"Category '{matched}' removed from saved categories. (Existing files on disk remain safe and untouched.)"


# ==============================================================================
# CUSTOM TAG MANAGEMENT (METADATA MODEL)
# ==============================================================================

def get_custom_tags() -> List[str]:
    """
    Return the list of saved custom tags from project.json.
    """
    config, _ = load_config()
    if config and isinstance(config.get("tags"), dict):
        custom = config["tags"].get("custom", [])
        if isinstance(custom, list):
            seen = set()
            result = []
            for t in custom:
                clean_t = normalize_metadata_display(t)
                norm_k = normalize_metadata_key(t)
                if norm_k and norm_k not in seen:
                    seen.add(norm_k)
                    result.append(clean_t)
            return result
    return []


def get_all_tags() -> List[str]:
    """
    Return all available tags: Built-in tags + Saved custom tags.
    """
    builtin_keys = {normalize_metadata_key(b) for b in BUILTIN_TAGS}
    custom = get_custom_tags()
    filtered_custom = [t for t in custom if normalize_metadata_key(t) not in builtin_keys]
    return list(BUILTIN_TAGS) + filtered_custom


def validate_tag_name(name: str) -> Tuple[bool, str]:
    """
    Validate a tag name:
    - Must not be empty.
    - Trims and collapses whitespace.
    - Case-insensitive duplicate check against built-in tags and saved custom tags.

    Returns:
        (is_valid, error_or_clean_name)
    """
    clean_name = normalize_metadata_display(name)
    norm_k = normalize_metadata_key(name)
    if not norm_k:
        return False, "Tag name cannot be empty."

    # Check against built-in tags
    for b in BUILTIN_TAGS:
        if norm_k == normalize_metadata_key(b):
            return False, f"'{clean_name}' is already a built-in tag (matches '{b}')."

    # Check against saved custom tags
    saved = get_custom_tags()
    for s in saved:
        if norm_k == normalize_metadata_key(s):
            return False, f"Tag '{clean_name}' is already saved (matches '{s}')."

    return True, clean_name


def save_custom_tag(name: str) -> Tuple[bool, str]:
    """
    Validate and save a new custom tag into project.json.
    """
    is_valid, clean_or_err = validate_tag_name(name)
    if not is_valid:
        return False, clean_or_err

    clean_name = clean_or_err
    norm_k = normalize_metadata_key(clean_name)

    config, err = load_config()
    if err:
        return False, f"Failed to load configuration: {err}"
    if config is None:
        config = {"default_language": "cpp"}

    tags_dict = config.setdefault("tags", {})
    if not isinstance(tags_dict, dict):
        tags_dict = {}
        config["tags"] = tags_dict

    custom_list = tags_dict.setdefault("custom", [])
    if not isinstance(custom_list, list):
        custom_list = []
        tags_dict["custom"] = custom_list

    for t in custom_list:
        if normalize_metadata_key(t) == norm_k:
            return False, f"Tag '{clean_name}' is already saved (matches '{t}')."

    custom_list.append(clean_name)

    config_file = get_config_path()
    ok, msg = _write_and_verify_json(config_file, config)
    if not ok:
        return False, f"Failed to save custom tag: {msg}"

    return True, f"Tag '{clean_name}' saved successfully."


def delete_custom_tag(name: str) -> Tuple[bool, str]:
    """
    Remove a saved custom tag from project.json.
    """
    clean_name = normalize_metadata_display(name)
    norm_k = normalize_metadata_key(name)
    if not norm_k:
        return False, "Tag name cannot be empty."

    for b in BUILTIN_TAGS:
        if norm_k == normalize_metadata_key(b):
            return False, f"Cannot delete built-in tag '{clean_name}'."

    config, err = load_config()
    if err or not config:
        return False, f"Could not load configuration: {err}"

    tags_dict = config.get("tags", {})
    if not isinstance(tags_dict, dict):
        return False, "No custom tags configured."

    custom_list = tags_dict.get("custom", [])
    if not isinstance(custom_list, list):
        return False, "No custom tags configured."

    matched = None
    for t in custom_list:
        if normalize_metadata_key(t) == norm_k:
            matched = str(t).strip()
            break

    if not matched:
        return False, f"Tag '{clean_name}' is not in saved tags."

    new_list = [t for t in custom_list if normalize_metadata_key(t) != norm_k]
    tags_dict["custom"] = new_list

    config_file = get_config_path()
    ok, msg = _write_and_verify_json(config_file, config)
    if not ok:
        return False, f"Failed to update configuration: {msg}"

    return True, f"Tag '{matched}' removed from saved tags."



# ==============================================================================
# PHASE 1 & PHASE 1.5 FUNCTIONS
# ==============================================================================


def get_language_extension(language: str) -> str:
    """
    Map a supported language to its standard file extension.
    Raises ValueError if language is unsupported.
    """
    normalized = language.strip()
    alias_map = {
        "c++": "C++",
        "cpp": "C++",
        "java": "Java",
        "python": "Python",
        "py": "Python",
    }
    canonical = alias_map.get(normalized.lower(), normalized)
    if canonical in SUPPORTED_LANGUAGES:
        return SUPPORTED_LANGUAGES[canonical]
    raise ValueError(f"Unsupported language: '{language}'. Supported: {list(SUPPORTED_LANGUAGES.keys())}")


def sanitize_title_to_filename(title: str) -> str:
    """
    Convert a problem title into a PascalCase alphanumeric filename without extension.
    Removes invalid characters and prevents directory traversal.

    Examples:
        'Two Sum' -> 'TwoSum'
        'Reverse Linked List' -> 'ReverseLinkedList'
        'Find: A/B?' -> 'FindAB'
        '3Sum' -> '3Sum'
    """
    if not title or not title.strip():
        return ""

    words = re.findall(r"[A-Za-z0-9]+", title)
    if not words:
        return ""

    pascal_words = []
    for w in words:
        if w.islower():
            pascal_words.append(w.capitalize())
        else:
            pascal_words.append(w)

    return "".join(pascal_words)


def generate_filename(title: str, language: str) -> str:
    """
    Generate a simple, safe filename for the problem title and language.

    Example:
        generate_filename('Two Sum', 'C++') -> 'TwoSum.cpp'
    """
    ext = get_language_extension(language)
    base = sanitize_title_to_filename(title)
    if not base:
        return ""
    return f"{base}{ext}"


def resolve_category_dir(repo_path: Path, category: str) -> Path:
    """
    Resolve the destination folder for a category inside repo_path.
    If an existing directory matches (case-insensitively), reuse it.
    Otherwise, return repo_path / category.
    """
    if repo_path.is_dir():
        for child in repo_path.iterdir():
            if child.is_dir() and child.name.lower() == category.lower():
                return child
    return repo_path / category


def generate_problem_content(
    title: str,
    platform: str,
    language: str,
    category: str,
    description: str,
    solution_code: str,
    created_date: Optional[str] = None,
    concepts: Optional[str] = None,
    data_structures: Optional[str] = None,
    time_complexity: Optional[str] = None,
    space_complexity: Optional[str] = None,
    tags: Optional[str] = None,
    importance: Optional[int | str] = None,
) -> str:
    """
    Generate the source file content containing the standardized metadata header
    followed by the original user solution code.
    """
    if created_date is None:
        created_date = date.today().strftime("%Y-%m-%d")

    clean_concepts = (concepts or "").strip()
    clean_ds = (data_structures or "").strip()
    clean_tags = (tags or "").strip()

    # Importance: numeric 1-5
    if importance is None or str(importance).strip() == "":
        clean_importance = "3"
    else:
        first_digit = re.search(r"[1-5]", str(importance))
        clean_importance = first_digit.group(0) if first_digit else "3"

    clean_time = (time_complexity or "Unable to determine").strip()
    clean_space = (space_complexity or "Unable to determine").strip()

    divider = "=" * 50
    header_body = (
        f"{divider}\n"
        f"Problem: {title.strip()}\n"
        f"Platform: {platform.strip()}\n"
        f"Language: {language.strip()}\n\n"
        f"Primary Category: {category.strip()}\n"
        f"Concepts / Techniques: {clean_concepts}\n"
        f"Data Structures: {clean_ds}\n"
        f"Tags: {clean_tags}\n"
        f"Importance: {clean_importance}\n\n"
        f"Time Complexity: {clean_time}\n"
        f"Space Complexity: {clean_space}\n\n"
        f"Added: {created_date}\n\n"
        f"Problem Description:\n"
        f"{description.strip()}\n"
        f"{divider}"
    )

    norm_lang = language.strip().lower()
    if norm_lang in ("python", "py"):
        header = f'"""\n{header_body}\n"""\n\n'
    else:
        # C++, Java, and standard C-style comment syntax
        header = f"/*\n{header_body}\n*/\n\n"

    # Retain the user's solution code exactly as entered
    return header + solution_code


def create_problem_file(
    title: str,
    platform: str,
    language: str,
    category: str,
    description: str,
    solution_code: str,
    custom_platform: Optional[str] = None,
    repo_path: Optional[str | Path] = None,
    concepts: Optional[str] = None,
    data_structures: Optional[str] = None,
    time_complexity: Optional[str] = None,
    space_complexity: Optional[str] = None,
    tags: Optional[str] = None,
    importance: Optional[int | str] = None,
) -> Tuple[bool, str, Optional[Path]]:
    """
    Validate, resolve destination, analyze complexity, generate content, write,
    and physically verify the creation of a new problem source file.

    Returns:
        (success, message, target_file_path)
    """
    # 1. Resolve and validate repository
    if repo_path is None:
        config, load_err = load_config()
        if load_err or not config:
            return False, f"Unable to load configuration: {load_err}", None
        repo_path = config.get("repository", "")

    is_repo_valid, repo_msg = validate_repository(repo_path)
    if not is_repo_valid:
        return False, f"Repository error: {repo_msg}", None

    repo_root = Path(repo_path).resolve()

    # 2. Validate input fields
    clean_title = (title or "").strip()
    if not clean_title:
        return False, "Problem title is required.", None

    # Path traversal check on raw title
    if ".." in clean_title:
        return False, "Unsafe problem title: path traversal ('..') is not permitted.", None

    clean_description = (description or "").strip()
    if not clean_description:
        return False, "Problem description is required.", None

    clean_code = (solution_code or "").strip()
    if not clean_code:
        return False, "Solution code is required.", None

    # Platform resolution
    clean_platform = (platform or "").strip()
    if not clean_platform:
        return False, "Platform selection is required.", None

    if clean_platform.lower() == "other":
        if not custom_platform or not custom_platform.strip():
            return False, "Please specify the custom platform name.", None
        raw_platform = custom_platform.strip()
    else:
        raw_platform = clean_platform

    plat_map = build_canonical_mapping(get_all_platforms(), [])
    resolved_platform = canonicalize_value(raw_platform, plat_map)

    # Language resolution
    clean_language = (language or "").strip()
    if not clean_language:
        return False, "Language selection is required.", None

    try:
        get_language_extension(clean_language)
    except ValueError as err:
        return False, str(err), None

    # Category validation
    clean_category = (category or "").strip()
    if not clean_category:
        return False, "Primary category selection is required.", None

    if ".." in clean_category or "/" in clean_category or "\\" in clean_category or ":" in clean_category:
        return False, "Unsafe category name: path traversal or invalid characters are not permitted.", None

    cat_map = build_canonical_mapping(get_categories(), [])
    matched_category = canonicalize_value(clean_category, cat_map)

    # Canonicalize token lists
    _, clean_concepts = canonicalize_token_list(concepts or "", build_canonical_mapping(BUILTIN_CONCEPTS, []))
    _, clean_ds = canonicalize_token_list(data_structures or "", build_canonical_mapping(BUILTIN_DATA_STRUCTURES, []))
    _, clean_tags = canonicalize_token_list(tags or "", build_canonical_mapping(get_all_tags(), []))

    # 3. Filename generation and sanitization
    filename = generate_filename(clean_title, clean_language)
    if not filename:
        return False, "Invalid problem title: could not generate a valid filename.", None

    # 4. Resolve category folder (first-class top-level folder directly under repo_root)
    category_dir = resolve_category_dir(repo_root, matched_category)
    resolved_cat_dir = category_dir.resolve()

    # Path traversal check on category folder
    if resolved_cat_dir.parent != repo_root.resolve():
        return False, "Path traversal error: category directory escapes repository root.", None

    # 5. Path safety check: Ensure target does not escape category folder or repo root
    target_file = (category_dir / filename).resolve()

    if target_file.parent != resolved_cat_dir:
        return False, "Path traversal error: target file escapes category directory.", None

    # 6. Duplicate check: Never silently overwrite existing file
    if target_file.exists():
        return (
            False,
            f"A file named '{filename}' already exists in '{category_dir.name}'.\n"
            "Creation cancelled to prevent overwriting existing solutions.",
            None,
        )

    # 7. Complexity analysis (Engine-determined)
    if time_complexity is None or space_complexity is None:
        try:
            complexity_data = analyze_complexity(clean_language, clean_code)
            if time_complexity is None:
                time_complexity = complexity_data.get("time_complexity", "Unable to determine")
            if space_complexity is None:
                space_complexity = complexity_data.get("space_complexity", "Unable to determine")
        except Exception as exc:
            return False, f"Complexity analysis failed unexpectedly: {exc}", None

    # 8. Generate content
    file_content = generate_problem_content(
        title=clean_title,
        platform=resolved_platform,
        language=clean_language,
        category=matched_category,
        description=clean_description,
        solution_code=solution_code,  # Preserve exact code spacing as entered
        concepts=clean_concepts,
        data_structures=clean_ds,
        time_complexity=time_complexity,
        space_complexity=space_complexity,
        tags=clean_tags,
        importance=importance,
    )

    # 9. Write file to disk
    try:
        category_dir.mkdir(parents=False, exist_ok=True)
        if not category_dir.is_dir():
            return False, f"Failed to create category directory: {category_dir}", None

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(file_content)
            f.flush()
            os.fsync(f.fileno())

    except Exception as exc:
        return False, f"Problem creation failed.\nReason: {exc}", None

    # 10. Physical verification
    if not target_file.exists():
        return False, f"File creation could not be verified: file missing on disk at {target_file}", None

    if not target_file.is_file():
        return False, f"File creation could not be verified: path is not a file at {target_file}", None

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            read_back = f.read()

        if read_back != file_content:
            return False, "File creation could not be verified: content read back does not match expected content.", None

        # Verify complexity and metadata is physically present in the file
        if f"Time Complexity: {time_complexity}" not in read_back or f"Space Complexity: {space_complexity}" not in read_back:
            return False, "File creation could not be verified: complexity metadata missing in read-back content.", None

    except Exception as exc:
        return False, f"Physical verification failed while reading back file: {exc}", None

    # 11. Success report
    clean_concepts_disp = concepts.strip() if concepts and concepts.strip() else "(None)"
    clean_ds_disp = data_structures.strip() if data_structures and data_structures.strip() else "(None)"
    clean_tags_disp = tags.strip() if tags and tags.strip() else "(None)"
    
    first_digit = re.search(r"[1-5]", str(importance)) if importance else None
    clean_imp_disp = first_digit.group(0) if first_digit else "3"

    success_msg = (
        "Problem created successfully.\n\n"
        f"Problem:\n{clean_title}\n\n"
        f"Category:\n{matched_category}\n\n"
        f"Concepts / Techniques:\n{clean_concepts_disp}\n\n"
        f"Data Structures:\n{clean_ds_disp}\n\n"
        f"Tags:\n{clean_tags_disp}\n\n"
        f"Importance:\n{clean_imp_disp}\n\n"
        f"Time Complexity:\n{time_complexity}\n\n"
        f"Space Complexity:\n{space_complexity}\n\n"
        f"File:\n{target_file}\n\n"
        "✓ File exists\n"
        "✓ Content verified"
    )
    return True, success_msg, target_file


# ==============================================================================
# PHASE 2: GIT INTEGRATION
# ==============================================================================

def is_git_available() -> Tuple[bool, str]:
    """
    Detect whether Git is installed and reachable on the system PATH.

    Returns:
        (is_available, version_or_error_message)
    """
    git_exe = shutil.which("git")
    if not git_exe:
        return False, "Git is not installed or not found on PATH."

    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"Git executable found but returned an error: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, "Git is not installed or not found on PATH."
    except subprocess.TimeoutExpired:
        return False, "Git version check timed out."
    except Exception as exc:
        return False, f"Git availability check failed: {exc}"


def get_git_repo_root(repo_path: "str | Path") -> Tuple[bool, str, Optional[Path]]:
    """
    Determine whether the path is inside a Git repository and return the Git repository root.
    Uses 'git -C <local_path> rev-parse --show-toplevel'.

    Returns:
        (is_repo, message, git_root_path)
    """
    if not repo_path or str(repo_path).strip() == "":
        return False, "No repository path provided.", None

    resolved = Path(repo_path).resolve()
    if not resolved.exists():
        return False, f"Path does not exist: {resolved}", None
    if not resolved.is_dir():
        return False, f"Path is not a directory: {resolved}", None

    is_avail, avail_msg = is_git_available()
    if not is_avail:
        return False, avail_msg, None

    try:
        result = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            top_level = result.stdout.strip()
            if top_level:
                git_root = Path(top_level).resolve()
                return True, "Git repository detected.", git_root
        return False, "The configured directory is not inside a Git repository.", None
    except FileNotFoundError:
        return False, "Git is not installed or not found on PATH.", None
    except subprocess.TimeoutExpired:
        return False, "Git repository check timed out.", None
    except Exception as exc:
        return False, f"Git repository check failed: {exc}", None


def is_git_repository(repo_path: "str | Path") -> Tuple[bool, str]:
    """
    Verify that the given directory is inside a Git working tree.
    Does NOT run git init. Never modifies the filesystem.

    Returns:
        (is_repo, message)
    """
    ok, msg, _ = get_git_repo_root(repo_path)
    return ok, msg


def get_git_remotes(repo_path: "str | Path") -> Tuple[bool, str, Dict[str, str]]:
    """
    Get configured Git remotes for the repository using 'git -C <root> remote -v'.

    Returns:
        (success, message, remotes_dict) e.g. {"origin": "https://github.com/..."}
    """
    ok, msg, root = get_git_repo_root(repo_path)
    if not ok or not root:
        return False, msg, {}

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "-v"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            return False, f"git remote -v failed: {err}", {}

        remotes: Dict[str, str] = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                name, url = parts[0], parts[1]
                remotes[name] = url

        if not remotes:
            return True, "No Git remote configured", {}
        return True, "Remotes retrieved.", remotes
    except Exception as exc:
        return False, f"Failed to get git remotes: {exc}", {}


def set_git_remote(repo_path: "str | Path", remote_url: str, remote_name: str = "origin") -> Tuple[bool, str]:
    """
    Add or update a Git remote safely.
    If the remote already exists, updates it using 'git remote set-url'.
    If the remote does not exist, adds it using 'git remote add'.
    Never blindly runs git remote add when origin exists.
    """
    clean_url = (remote_url or "").strip()
    if not clean_url:
        return False, "Remote URL cannot be empty."

    clean_name = (remote_name or "origin").strip()

    ok, msg, root = get_git_repo_root(repo_path)
    if not ok or not root:
        return False, msg

    remotes_ok, _, remotes = get_git_remotes(root)
    if not remotes_ok:
        return False, "Could not inspect existing remotes."

    try:
        if clean_name in remotes:
            cmd = ["git", "-C", str(root), "remote", "set-url", clean_name, clean_url]
            action = "updated"
        else:
            cmd = ["git", "-C", str(root), "remote", "add", clean_name, clean_url]
            action = "added"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return True, f"Remote '{clean_name}' {action} successfully to {clean_url}"
        err = result.stderr.strip() or result.stdout.strip()
        return False, f"Failed to set remote: {err}"
    except Exception as exc:
        return False, f"Failed to set remote: {exc}"


def verify_git_configuration(repo_path: "str | Path", remote_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform complete 8-step verification of Git configuration:
    1. Local path exists
    2. Local path is a directory
    3. Git executable is available
    4. Local path is inside a Git repository
    5. Determine actual Git repository root
    6. Read current remotes
    7. Compare configured remote with repository remote (and safely update if requested)
    8. Report the final Git state
    """
    report: Dict[str, Any] = {
        "success": False,
        "steps": [],
        "git_available": False,
        "is_repo": False,
        "repo_root": None,
        "remote_name": None,
        "remote_url": None,
        "message": "",
    }

    if not repo_path or str(repo_path).strip() == "":
        report["message"] = "No repository path provided."
        return report

    resolved_path = Path(repo_path).resolve()

    # Step 1: Local path exists
    if not resolved_path.exists():
        report["steps"].append((False, f"Path does not exist: {resolved_path}"))
        report["message"] = f"Repository path does not exist: {resolved_path}"
        return report
    report["steps"].append((True, f"Local path exists: {resolved_path}"))

    # Step 2: Local path is a directory
    if not resolved_path.is_dir():
        report["steps"].append((False, f"Path is not a directory: {resolved_path}"))
        report["message"] = f"Selected path is not a directory: {resolved_path}"
        return report
    report["steps"].append((True, "Local path is a directory"))

    # Step 3: Git executable is available
    avail_ok, avail_msg = is_git_available()
    if not avail_ok:
        report["steps"].append((False, avail_msg))
        report["message"] = avail_msg
        return report
    report["git_available"] = True
    report["steps"].append((True, f"Git available ({avail_msg})"))

    # Steps 4 & 5: Inside Git repository & determine actual Git repository root
    repo_ok, repo_msg, root_path = get_git_repo_root(resolved_path)
    if not repo_ok or not root_path:
        report["steps"].append((False, repo_msg))
        report["message"] = repo_msg
        return report

    report["is_repo"] = True
    report["repo_root"] = root_path
    report["steps"].append((True, f"Git repository found (Root: {root_path})"))

    # Step 6: Read current remotes
    remotes_ok, remotes_msg, remotes = get_git_remotes(root_path)
    if not remotes_ok:
        report["steps"].append((False, f"Could not read remotes: {remotes_msg}"))
    else:
        report["steps"].append((True, f"Read current remotes ({len(remotes)} configured)"))

    # Step 7: Compare configured remote with repository remote / update if requested
    clean_target_url = (remote_url or "").strip()
    current_origin_url = remotes.get("origin")

    if clean_target_url:
        if current_origin_url != clean_target_url:
            set_ok, set_msg = set_git_remote(root_path, clean_target_url, "origin")
            if set_ok:
                report["steps"].append((True, f"Updated remote origin to: {clean_target_url}"))
                report["remote_name"] = "origin"
                report["remote_url"] = clean_target_url
            else:
                report["steps"].append((False, f"Failed to update remote: {set_msg}"))
                report["remote_name"] = "origin" if current_origin_url else None
                report["remote_url"] = current_origin_url
        else:
            report["remote_name"] = "origin"
            report["remote_url"] = current_origin_url
            report["steps"].append((True, f"Remote origin already matches: {clean_target_url}"))
    else:
        if current_origin_url:
            report["remote_name"] = "origin"
            report["remote_url"] = current_origin_url
            report["steps"].append((True, f"Existing remote origin: {current_origin_url}"))
        elif remotes:
            first_key = list(remotes.keys())[0]
            report["remote_name"] = first_key
            report["remote_url"] = remotes[first_key]
            report["steps"].append((True, f"Existing remote {first_key}: {remotes[first_key]}"))
        else:
            report["steps"].append((True, "No Git remote configured"))

    # Step 8: Report final Git state
    report["success"] = True
    status_lines = [
        "✓ Git available",
        "✓ Git repository found",
        f"✓ Repository root: {root_path}",
    ]
    if report["remote_url"]:
        status_lines.append(f"✓ Remote: {report['remote_name']}")
        status_lines.append(f"✓ Remote URL: {report['remote_url']}")
    else:
        status_lines.append("⚠ No Git remote configured")

    report["message"] = "\n".join(status_lines)
    return report


def get_git_status(repo_path: "str | Path") -> Tuple[bool, str, str]:
    """
    Run 'git status --short' against the verified repository root.

    Returns:
        (success, message, short_status_output)
    """
    ok, msg, root = get_git_repo_root(repo_path)
    if not ok or not root:
        return False, msg, ""

    resolved_root = root.resolve()

    try:
        result = subprocess.run(
            ["git", "-C", str(resolved_root), "status", "--short"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return True, "Working tree is clean.", ""
            return True, "Git status retrieved.", output
        error = result.stderr.strip() or result.stdout.strip()
        return False, f"git status failed: {error}", ""
    except FileNotFoundError:
        return False, "Git is not installed.", ""
    except subprocess.TimeoutExpired:
        return False, "git status timed out.", ""
    except Exception as exc:
        return False, f"git status failed: {exc}", ""


def git_add_file(repo_path: "str | Path", file_path: "str | Path") -> Tuple[bool, str]:
    """
    Stage a single, specific file using 'git add -- <file>'.
    Executes against the verified Git repository root.

    Safety guarantees:
    - Only the exact file_path argument is staged; no wildcards, no shell expansion.
    - file_path must resolve to a location inside verified repo root (path traversal guard).
    - shell=True is never used.

    Returns:
        (success, message)
    """
    ok, msg, root = get_git_repo_root(repo_path)
    if not ok or not root:
        return False, msg

    resolved_root = root.resolve()
    resolved_file = Path(file_path).resolve()

    # Path traversal guard: file must be inside the verified repo root
    try:
        rel_path = resolved_file.relative_to(resolved_root)
    except ValueError:
        return False, f"Safety error: file is outside the repository root.\nFile: {resolved_file}\nRepo root: {resolved_root}"

    if not resolved_file.exists():
        return False, f"File does not exist on disk: {resolved_file}"
    if not resolved_file.is_file():
        return False, f"Path is not a file: {resolved_file}"

    try:
        result = subprocess.run(
            ["git", "-C", str(resolved_root), "add", "--", str(rel_path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return True, f"Staged: {resolved_file.name}"
        error = result.stderr.strip() or result.stdout.strip()
        return False, f"git add failed: {error}"
    except FileNotFoundError:
        return False, "Git is not installed."
    except subprocess.TimeoutExpired:
        return False, "git add timed out."
    except Exception as exc:
        return False, f"git add failed: {exc}"


def git_commit(repo_path: "str | Path", message: str) -> Tuple[bool, str]:
    """
    Create a commit using the user-supplied message against verified repository root.

    Safety guarantees:
    - The commit message is passed as a list argument; never shell-interpolated.
    - shell=True is never used.
    - No credential handling.
    - Requires the user to have already staged changes (via git_add_file).

    Returns:
        (success, message_or_error)
    """
    clean_message = (message or "").strip()
    if not clean_message:
        return False, "Commit message is required and must not be empty."

    ok, msg, root = get_git_repo_root(repo_path)
    if not ok or not root:
        return False, msg

    resolved_root = root.resolve()

    try:
        # Part 9: Verify there is something staged before committing
        diff_res = subprocess.run(
            ["git", "-C", str(resolved_root), "diff", "--cached", "--quiet"],
            capture_output=True,
            timeout=10,
        )
        if diff_res.returncode == 0:
            return False, "Nothing staged to commit."

        result = subprocess.run(
            ["git", "-C", str(resolved_root), "commit", "-m", clean_message],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            return True, f"Commit successful.\n{output}"
        error = result.stderr.strip() or result.stdout.strip()
        if "nothing to commit" in error.lower() or "nothing added to commit" in error.lower():
            return False, "Nothing staged to commit."
        return False, f"git commit failed:\n{error}"
    except FileNotFoundError:
        return False, "Git is not installed."
    except subprocess.TimeoutExpired:
        return False, "git commit timed out."
    except Exception as exc:
        return False, f"git commit failed: {exc}"


def git_push(repo_path: "str | Path") -> Tuple[bool, str]:
    """
    Push committed changes to the configured remote using 'git push'.

    Before pushing:
    1. Verify Git repository
    2. Verify remote exists
    3. Run push

    Safety guarantees:
    - Uses the repository's existing remote/branch configuration.
    - No credential storage or handling.
    - shell=True is never used.
    - Authentication is delegated entirely to the user's git config / credential helper.

    Returns:
        (success, output_or_error)
    """
    ok, msg, root = get_git_repo_root(repo_path)
    if not ok or not root:
        return False, msg

    resolved_root = root.resolve()

    # Verify remote exists
    remotes_ok, _, remotes = get_git_remotes(resolved_root)
    if not remotes_ok or not remotes:
        return False, "Cannot push: no Git remote is configured."

    try:
        result = subprocess.run(
            ["git", "-C", str(resolved_root), "push"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            combined = (result.stdout + "\n" + result.stderr).strip()
            return True, f"Push successful.\n{combined}" if combined else "Push successful."
        error = (result.stderr + "\n" + result.stdout).strip()
        return False, f"git push failed:\n{error}"
    except FileNotFoundError:
        return False, "Git is not installed."
    except subprocess.TimeoutExpired:
        return False, "git push timed out (60 s). Check your network or remote configuration."
    except Exception as exc:
        return False, f"git push failed: {exc}"


# ==============================================================================
# PHASE 3.5: REPOSITORY RESCAN, METADATA PARSING, VALIDATION & REPAIR
# ==============================================================================

# Directories to skip when scanning a DSA repository
SCAN_EXCLUDE_DIRS = {
    ".git",
    ".vscode",
    ".idea",
    ".gemini",
    ".agents",
    "__pycache__",
    "build",
    "dist",
    "bin",
    "obj",
    "node_modules",
}

# Recognized file extensions for DSA solutions
RECOGNIZED_EXTENSIONS = {".cpp", ".java", ".py"}


def extract_header_and_solution(content: str, language_or_ext: str = "") -> Tuple[bool, str, str]:
    """
    Extract the top block comment (metadata header) and the remaining solution code.

    Returns:
        (has_header, header_raw_text, solution_code)
    """
    if not content:
        return False, "", ""

    # 1. C/Java style block comment /* ... */ at top of file
    c_match = re.match(r"^\s*/\*(.*?)\*/(?:\r?\n)*", content, re.DOTALL)
    if c_match:
        return True, c_match.group(1), content[c_match.end():]

    # 2. Python style triple-double quotes \"\"\" ... \"\"\"
    py_match_d = re.match(r'^\s*"""(.*?)"""(?:\r?\n)*', content, re.DOTALL)
    if py_match_d:
        return True, py_match_d.group(1), content[py_match_d.end():]

    # 3. Python style triple-single quotes ''' ... '''
    py_match_s = re.match(r"^\s*\'\'\'(.*?)\'\'\'(?:\r?\n)*", content, re.DOTALL)
    if py_match_s:
        return True, py_match_s.group(1), content[py_match_s.end():]

    return False, "", content


def parse_header_text(header_text: str) -> Dict[str, Any]:
    """
    Parse standardized key-value pairs and description from a header comment block.

    Returns a dictionary containing the parsed metadata, present_fields set, and is_dsa_header boolean.
    """
    lines = header_text.replace("\r\n", "\n").split("\n")

    present_fields = set()
    data = {
        "title": "",
        "platform": "",
        "language": "",
        "category": "",
        "concepts": "",
        "data_structures": "",
        "tags": "",
        "importance": "",
        "time_complexity": "",
        "space_complexity": "",
        "added_date": "",
        "description": "",
    }

    in_desc = False
    desc_lines: List[str] = []

    for line in lines:
        stripped = line.strip()

        # Check for divider lines (e.g. ========== or ----------)
        if re.match(r"^[=\-]{5,}$", stripped):
            if in_desc:
                # End of description block reached by divider
                break
            continue

        if in_desc:
            desc_lines.append(line)
            continue

        if not stripped:
            continue

        # Strip optional leading asterisk (e.g. javadoc style ' * Problem: ...')
        if stripped.startswith("*") and not re.match(r"^\*{3,}$", stripped):
            stripped = stripped.lstrip("*").strip()

        if not stripped:
            continue

        # Match metadata keys
        m_prob = re.match(r"^Problem:\s*(.*)$", stripped, re.IGNORECASE)
        if m_prob:
            present_fields.add("Problem")
            data["title"] = m_prob.group(1).strip()
            continue

        m_plat = re.match(r"^Platform:\s*(.*)$", stripped, re.IGNORECASE)
        if m_plat:
            present_fields.add("Platform")
            data["platform"] = m_plat.group(1).strip()
            continue

        m_lang = re.match(r"^Language:\s*(.*)$", stripped, re.IGNORECASE)
        if m_lang:
            present_fields.add("Language")
            data["language"] = m_lang.group(1).strip()
            continue

        m_cat = re.match(r"^(?:Primary Category|Category):\s*(.*)$", stripped, re.IGNORECASE)
        if m_cat:
            present_fields.add("Primary Category")
            data["category"] = m_cat.group(1).strip()
            continue

        m_conc = re.match(r"^(?:Concepts / Techniques|Concepts|Techniques):\s*(.*)$", stripped, re.IGNORECASE)
        if m_conc:
            present_fields.add("Concepts / Techniques")
            data["concepts"] = m_conc.group(1).strip()
            continue

        m_ds = re.match(r"^(?:Data Structures|Data Structure):\s*(.*)$", stripped, re.IGNORECASE)
        if m_ds:
            present_fields.add("Data Structures")
            data["data_structures"] = m_ds.group(1).strip()
            continue

        m_tag = re.match(r"^Tags:\s*(.*)$", stripped, re.IGNORECASE)
        if m_tag:
            present_fields.add("Tags")
            data["tags"] = m_tag.group(1).strip()
            continue

        m_imp = re.match(r"^Importance:\s*(.*)$", stripped, re.IGNORECASE)
        if m_imp:
            present_fields.add("Importance")
            raw_imp = m_imp.group(1).strip()
            dig = re.search(r"[1-5]", raw_imp)
            data["importance"] = dig.group(0) if dig else raw_imp
            continue

        m_tc = re.match(r"^Time Complexity:\s*(.*)$", stripped, re.IGNORECASE)
        if m_tc:
            present_fields.add("Time Complexity")
            data["time_complexity"] = m_tc.group(1).strip()
            continue

        m_sc = re.match(r"^Space Complexity:\s*(.*)$", stripped, re.IGNORECASE)
        if m_sc:
            present_fields.add("Space Complexity")
            data["space_complexity"] = m_sc.group(1).strip()
            continue

        m_add = re.match(r"^(?:Added|Added Date|Date):\s*(.*)$", stripped, re.IGNORECASE)
        if m_add:
            present_fields.add("Added")
            data["added_date"] = m_add.group(1).strip()
            continue

        m_desc = re.match(r"^(?:Problem Description|Description):\s*(.*)$", stripped, re.IGNORECASE)
        if m_desc:
            present_fields.add("Problem Description")
            in_desc = True
            first_line = m_desc.group(1).strip()
            if first_line:
                desc_lines.append(first_line)
            continue

    if "Problem Description" in present_fields:
        data["description"] = "\n".join(desc_lines).strip()

    # Determine if this looks like a recognizable DSA Organizer header
    # At least Problem, Platform, or Primary Category must be present
    is_dsa = bool({"Problem", "Platform", "Primary Category", "Language"} & present_fields)
    data["present_fields"] = list(present_fields)
    data["is_dsa_header"] = is_dsa
    return data


def parse_problem_content(content: str, language_or_ext: str = "") -> Dict[str, Any]:
    """
    Parse a problem file's content into metadata dictionary and solution code.
    """
    has_header, header_raw, solution_code = extract_header_and_solution(content, language_or_ext)
    if not has_header:
        return {
            "valid_header": False,
            "raw_header": "",
            "solution_code": content,
            "present_fields": [],
            "title": "",
            "platform": "",
            "language": "",
            "category": "",
            "concepts": "",
            "data_structures": "",
            "tags": "",
            "importance": "",
            "time_complexity": "",
            "space_complexity": "",
            "added_date": "",
            "description": "",
        }

    parsed = parse_header_text(header_raw)
    parsed["valid_header"] = parsed["is_dsa_header"]
    parsed["raw_header"] = header_raw
    parsed["solution_code"] = solution_code
    return parsed


def parse_problem_metadata(file_path: "str | Path") -> Dict[str, Any]:
    """
    Read and parse a problem source file from disk.
    """
    target = Path(file_path).resolve()
    if not target.exists() or not target.is_file():
        return {
            "valid_header": False,
            "error": f"File does not exist: {target}",
            "file_path": str(target),
            "filename": target.name,
            "solution_code": "",
            "present_fields": [],
        }

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = target.read_text(encoding="latin-1")
        except Exception as exc:
            return {
                "valid_header": False,
                "error": f"Could not read file: {exc}",
                "file_path": str(target),
                "filename": target.name,
                "solution_code": "",
                "present_fields": [],
            }

    ext = target.suffix
    meta = parse_problem_content(content, ext)
    meta["file_path"] = str(target)
    meta["filename"] = target.name
    return meta


def validate_problem_metadata(
    metadata: Dict[str, Any],
    folder_category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate parsed problem metadata against the Phase 3 standardized metadata model.

    Distinguishes:
    - Complete: All expected metadata fields exist and are valid.
    - Incomplete: Header exists, but one or more standardized fields are missing.
    - Unreadable / Unknown: No recognizable DSA Organizer metadata header.
    - Category Mismatch: Physical folder location differs from 'Primary Category' metadata.

    Returns:
        {
            "status": "complete" | "incomplete" | "unreadable",
            "is_complete": bool,
            "missing_fields": List[str],
            "category_mismatch": bool,
            "folder_category": str,
            "metadata_category": str,
        }
    """
    if not metadata.get("valid_header"):
        return {
            "status": "unreadable",
            "is_complete": False,
            "missing_fields": ["Unrecognized or missing metadata header"],
            "category_mismatch": False,
            "folder_category": folder_category or "",
            "metadata_category": metadata.get("category", ""),
        }

    present = set(metadata.get("present_fields", []))
    missing: List[str] = []

    # Mandatory non-empty fields
    if "Problem" not in present or not metadata.get("title", "").strip():
        missing.append("Problem")
    if "Platform" not in present or not metadata.get("platform", "").strip():
        missing.append("Platform")
    if "Language" not in present or not metadata.get("language", "").strip():
        missing.append("Language")
    if "Primary Category" not in present or not metadata.get("category", "").strip():
        missing.append("Primary Category")
    if "Added" not in present or not metadata.get("added_date", "").strip():
        missing.append("Added")

    # Importance: must be present and valid 1-5 digit
    if "Importance" not in present or str(metadata.get("importance", "")).strip() not in ("1", "2", "3", "4", "5"):
        missing.append("Importance")

    # Time Complexity & Space Complexity
    if "Time Complexity" not in present or not metadata.get("time_complexity", "").strip():
        missing.append("Time Complexity")
    if "Space Complexity" not in present or not metadata.get("space_complexity", "").strip():
        missing.append("Space Complexity")

    # Standard fields that may be empty strings, but the field key itself MUST exist in the header
    if "Concepts / Techniques" not in present:
        missing.append("Concepts / Techniques")
    if "Data Structures" not in present:
        missing.append("Data Structures")
    if "Tags" not in present:
        missing.append("Tags")
    if "Problem Description" not in present:
        missing.append("Problem Description")

    # Category Mismatch Check
    category_mismatch = False
    meta_cat = metadata.get("category", "").strip()
    if folder_category and meta_cat and folder_category.lower() != "dsa":
        if folder_category.strip().lower() != meta_cat.lower():
            category_mismatch = True

    status = "incomplete" if missing else "complete"
    is_complete = (status == "complete")

    return {
        "status": status,
        "is_complete": is_complete,
        "missing_fields": missing,
        "category_mismatch": category_mismatch,
        "folder_category": folder_category or "",
        "metadata_category": meta_cat,
    }


def scan_repository(repo_path: "str | Path") -> Dict[str, Any]:
    """
    Scan the configured DSA repository for all .cpp, .java, and .py solution files.

    Performs read-only inspection:
    - Never modifies, moves, stages, or commits any files.
    - Recognizes top-level category folders.
    - Parses headers and validates metadata against the complete model.
    - Detects missing fields, malformed headers, and category mismatches.

    Returns summary counts and a list of detailed problem records.
    """
    is_val, val_msg = validate_repository(repo_path)
    if not is_val:
        return {
            "success": False,
            "error": val_msg,
            "total_problems": 0,
            "complete_count": 0,
            "incomplete_count": 0,
            "unreadable_count": 0,
            "mismatch_count": 0,
            "problems": [],
        }

    resolved_repo = Path(repo_path).resolve()
    problems: List[Dict[str, Any]] = []

    for root_dir, dirs, files in os.walk(resolved_repo):
        # Exclude hidden or non-source directories
        dirs[:] = [d for d in dirs if d not in SCAN_EXCLUDE_DIRS and not d.startswith(".")]

        current_dir = Path(root_dir)

        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext not in RECOGNIZED_EXTENSIONS:
                continue

            file_path = current_dir / filename
            try:
                rel_path = file_path.relative_to(resolved_repo)
            except ValueError:
                rel_path = Path(filename)

            # Determine folder category based on directory under repo root
            if len(rel_path.parts) > 1:
                folder_category = rel_path.parts[0]
            else:
                folder_category = "Uncategorized"

            parsed_meta = parse_problem_metadata(file_path)
            val_res = validate_problem_metadata(parsed_meta, folder_category=folder_category)

            # Fallback title if header was unreadable
            display_title = parsed_meta.get("title") or file_path.stem

            problems.append({
                "file_path": str(file_path),
                "rel_path": str(rel_path),
                "filename": filename,
                "title": display_title,
                "language": parsed_meta.get("language") or ("C++" if ext == ".cpp" else ("Java" if ext == ".java" else "Python")),
                "platform": parsed_meta.get("platform", ""),
                "category": parsed_meta.get("category", ""),
                "folder_category": folder_category,
                "status": val_res["status"],
                "is_complete": val_res["is_complete"],
                "missing_fields": val_res["missing_fields"],
                "category_mismatch": val_res["category_mismatch"],
                "metadata": parsed_meta,
            })

    # Sort problems alphabetically by title / filename
    problems.sort(key=lambda p: p["title"].lower())

    complete_count = sum(1 for p in problems if p["status"] == "complete")
    incomplete_count = sum(1 for p in problems if p["status"] == "incomplete")
    unreadable_count = sum(1 for p in problems if p["status"] == "unreadable")
    mismatch_count = sum(1 for p in problems if p["category_mismatch"])

    return {
        "success": True,
        "repo_path": str(resolved_repo),
        "total_problems": len(problems),
        "complete_count": complete_count,
        "incomplete_count": incomplete_count,
        "unreadable_count": unreadable_count,
        "mismatch_count": mismatch_count,
        "problems": problems,
    }


def relocate_problem_file(
    file_path: "str | Path",
    new_category: str,
    repo_path: Optional["str | Path"] = None,
) -> Tuple[bool, str, Optional[Path]]:
    """
    Physically relocate a problem file to a new primary category folder.

    Safety & Verification Guarantees:
    1. Validates category name against path traversal and invalid characters.
    2. Resolves destination directory inside the configured repository.
    3. Prevents destination file collisions (will not overwrite existing files).
    4. Preserves file contents and solution implementation byte-for-byte.
    5. Verifies destination existence and source removal.
    """
    target = Path(file_path).resolve()
    if not target.exists() or not target.is_file():
        return False, f"Source file does not exist: {target}", None

    clean_category = (new_category or "Uncategorized").strip()
    if ".." in clean_category or "/" in clean_category or "\\" in clean_category:
        return False, "Invalid category: path traversal or path separators not permitted.", None

    invalid_chars = set(r'<>:"/\|?*')
    if any(ch in invalid_chars for ch in clean_category):
        return False, f"Invalid category: contains forbidden characters.", None

    if repo_path:
        resolved_repo = Path(repo_path).resolve()
    else:
        cfg, _ = load_config()
        cfg_repo = (cfg or {}).get("repository") or (cfg or {}).get("repository_path")
        if cfg_repo and Path(cfg_repo).is_dir():
            resolved_repo = Path(cfg_repo).resolve()
        else:
            resolved_repo = target.parent.parent

    dest_dir = resolve_category_dir(resolved_repo, clean_category)
    dest_file = (dest_dir / target.name).resolve()

    if dest_file == target:
        return True, "File is already in the target category folder.", target

    if dest_file.exists():
        return False, f"Destination collision: '{dest_file.name}' already exists in folder '{dest_dir.name}'.", None

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = target.read_text(encoding="latin-1")

    # Create destination directory if needed
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Write to destination
    dest_file.write_text(content, encoding="utf-8")

    # Remove source
    target.unlink()

    # Verification
    if not dest_file.exists() or not dest_file.is_file():
        return False, "Verification failed: Relocated file not found at destination.", None
    if target.exists():
        return False, "Verification failed: Source file was not removed after relocation.", None

    return True, f"File relocated to {dest_dir.name}/{dest_file.name}.", dest_file


def update_problem_metadata(
    file_path: "str | Path",
    updated_fields: Dict[str, Any],
    repo_path: Optional["str | Path"] = None,
) -> Tuple[bool, str]:
    """
    Safely update the metadata header of a problem source file while preserving
    the user's solution code byte-for-byte unchanged.

    If the Primary Category is changed, the problem file is also physically relocated
    to the corresponding category folder inside the repository.

    Safety & Verification Guarantees:
    1. Read existing file and extract solution code.
    2. Merge updated metadata fields over existing values.
    3. Retain existing solution code without modification or added comments.
    4. If category changed:
       - Validate new category name (no path traversal).
       - Determine target category folder and destination path.
       - Prevent destination collisions (no silent overwrite).
       - Create destination directory if needed.
       - Write new content to destination and remove source.
       - Verify destination exists, source is removed, and solution code matches byte-for-byte.
    5. If category unchanged:
       - Write new content in-place to the exact same path.
       - Verify file exists, header matches, and solution matches byte-for-byte.
    6. Does NOT trigger any git operations (no auto-commit/push).
    """
    target = Path(file_path).resolve()
    if not target.exists() or not target.is_file():
        return False, f"File does not exist: {target}"

    # Read original content
    try:
        orig_content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            orig_content = target.read_text(encoding="latin-1")
        except Exception as exc:
            return False, f"Failed to read file: {exc}"

    # Parse original metadata and extract solution code
    parsed = parse_problem_content(orig_content, target.suffix)
    solution_code = parsed.get("solution_code", orig_content)

    # Determine fields, merging updated_fields over parsed values
    title = str(updated_fields.get("title") or parsed.get("title") or target.stem).strip()
    platform = str(updated_fields.get("platform") or parsed.get("platform") or "LeetCode").strip()

    # Determine language
    ext = target.suffix.lower()
    default_lang = "C++" if ext == ".cpp" else ("Java" if ext == ".java" else "Python")
    language = str(updated_fields.get("language") or parsed.get("language") or default_lang).strip()

    category = str(updated_fields.get("category") or parsed.get("category") or "Uncategorized").strip()
    if not category:
        category = "Uncategorized"

    # Category name safety checks
    if ".." in category or "/" in category or "\\" in category:
        return False, "Invalid category: path traversal or path separators not permitted."
    invalid_chars = set(r'<>:"/\|?*')
    if any(ch in invalid_chars for ch in category):
        return False, "Invalid category: contains forbidden characters."

    # Canonicalize metadata values
    plat_map = build_canonical_mapping(get_all_platforms(), [])
    platform = canonicalize_value(platform, plat_map)

    cat_map = build_canonical_mapping(get_categories(), [])
    category = canonicalize_value(category, cat_map)

    raw_concepts = str(updated_fields.get("concepts") if "concepts" in updated_fields else parsed.get("concepts", "")).strip()
    raw_ds = str(updated_fields.get("data_structures") if "data_structures" in updated_fields else parsed.get("data_structures", "")).strip()
    raw_tags = str(updated_fields.get("tags") if "tags" in updated_fields else parsed.get("tags", "")).strip()

    _, concepts = canonicalize_token_list(raw_concepts, build_canonical_mapping(BUILTIN_CONCEPTS, []))
    _, data_structures = canonicalize_token_list(raw_ds, build_canonical_mapping(BUILTIN_DATA_STRUCTURES, []))
    _, tags = canonicalize_token_list(raw_tags, build_canonical_mapping(get_all_tags(), []))

    importance = updated_fields.get("importance") if "importance" in updated_fields else parsed.get("importance", "3")
    added_date = str(updated_fields.get("added_date") or parsed.get("added_date") or date.today().strftime("%Y-%m-%d")).strip()
    description = str(updated_fields.get("description") if "description" in updated_fields else parsed.get("description", "")).strip()

    # Complexity
    tc = updated_fields.get("time_complexity") or parsed.get("time_complexity")
    sc = updated_fields.get("space_complexity") or parsed.get("space_complexity")

    if not tc or not sc or tc == "Unable to determine" or sc == "Unable to determine":
        est_tc, est_sc = analyze_complexity(solution_code, language)
        if not tc:
            tc = est_tc
        if not sc:
            sc = est_sc

    # Generate new source content
    new_content = generate_problem_content(
        title=title,
        platform=platform,
        language=language,
        category=category,
        description=description,
        solution_code=solution_code,
        created_date=added_date,
        concepts=concepts,
        data_structures=data_structures,
        time_complexity=tc,
        space_complexity=sc,
        tags=tags,
        importance=importance,
    )

    # Determine repository root
    if repo_path:
        resolved_repo = Path(repo_path).resolve()
    else:
        cfg, _ = load_config()
        cfg_repo = (cfg or {}).get("repository") or (cfg or {}).get("repository_path")
        if cfg_repo and Path(cfg_repo).is_dir():
            resolved_repo = Path(cfg_repo).resolve()
        else:
            resolved_repo = target.parent.parent

    # Determine destination category directory
    dest_dir = resolve_category_dir(resolved_repo, category)
    dest_file = (dest_dir / target.name).resolve()

    # Case 1: In-place update (Category folder unchanged)
    if dest_file == target:
        try:
            target.write_text(new_content, encoding="utf-8")
        except Exception as exc:
            return False, f"Failed to write updated file: {exc}"

        # Verification
        if not target.exists() or not target.is_file():
            return False, "Verification failed: File disappeared after write."

        try:
            read_back = target.read_text(encoding="utf-8")
        except Exception as exc:
            return False, f"Verification failed: Could not read back written file: {exc}"

        read_meta = parse_problem_content(read_back, target.suffix)
        if not read_meta.get("valid_header"):
            return False, "Verification failed: Header not recognized in updated file."

        read_solution = read_meta.get("solution_code", "")
        if read_solution != solution_code:
            return False, "Verification failed: Solution code was altered during metadata repair."

        return True, "Metadata updated successfully."

    # Case 2: Relocation required (Category changed)
    # Check for destination collision
    if dest_file.exists():
        return False, f"Destination collision: '{dest_file.name}' already exists in folder '{dest_dir.name}'. File was not moved."

    # Create destination directory
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return False, f"Failed to create destination folder '{dest_dir.name}': {exc}"

    # Write new content to destination file
    try:
        dest_file.write_text(new_content, encoding="utf-8")
    except Exception as exc:
        return False, f"Failed to write relocated file: {exc}"

    # Remove source file
    try:
        target.unlink()
    except Exception as exc:
        # If removing source failed, clean up destination to maintain atomic consistency
        if dest_file.exists():
            dest_file.unlink()
        return False, f"Failed to remove source file during relocation: {exc}"

    # 10-step Physical Verification on relocated file:
    # 1. Destination exists & is_file
    if not dest_file.exists() or not dest_file.is_file():
        return False, "Verification failed: Relocated file disappeared after write."

    # 2. Source file no longer exists
    if target.exists():
        return False, "Verification failed: Source file still exists at old location."

    # 3. Read back from destination
    try:
        read_back = dest_file.read_text(encoding="utf-8")
    except Exception as exc:
        return False, f"Verification failed: Could not read back relocated file: {exc}"

    # 4. Header validation
    read_meta = parse_problem_content(read_back, dest_file.suffix)
    if not read_meta.get("valid_header"):
        return False, "Verification failed: Header not recognized in relocated file."

    # 5. Solution code byte-for-byte preservation
    read_solution = read_meta.get("solution_code", "")
    if read_solution != solution_code:
        return False, "Verification failed: Solution code was altered during relocation."

    return True, f"Metadata updated and file relocated to {dest_dir.name}/{dest_file.name}."


# ==============================================================================
# METADATA DUPLICATE DETECTION & EXPLICIT NORMALIZATION
# ==============================================================================

def detect_metadata_duplicates(repo_path: "str | Path") -> Dict[str, Any]:
    """
    Inspect the repository for duplicate metadata variants across:
    - Platforms
    - Primary Categories
    - Tags
    - Concepts / Techniques
    - Data Structures
    - Category folder directory names

    Safety Guarantee:
    - Strictly READ-ONLY. Never modifies any files or directories on disk.
    - Groups distinct raw strings that share the same normalized identity key.
    - Identifies the deterministic canonical display value (built-in/configured > frequency > alphabetical).
    """
    scan_res = scan_repository(repo_path)
    if not scan_res.get("success"):
        return {
            "success": False,
            "error": scan_res.get("error", "Failed to scan repository"),
            "has_duplicates": False,
            "total_duplicate_groups": 0,
            "total_affected_files": 0,
            "duplicate_groups": [],
            "category_folder_duplicates": [],
        }

    resolved_repo = Path(repo_path).resolve()
    problems = scan_res.get("problems", [])

    # 1. Configured canonical pools
    configured_platforms = get_all_platforms()
    configured_categories = get_categories()
    configured_tags = get_all_tags()
    configured_concepts = list(BUILTIN_CONCEPTS)
    configured_ds = list(BUILTIN_DATA_STRUCTURES)

    # 2. Extract discovered raw values with occurrence tracking per file
    fields_data = {
        "Platform": {"configured": configured_platforms, "items": []},
        "Category": {"configured": configured_categories, "items": []},
        "Tags": {"configured": configured_tags, "items": []},
        "Concepts / Techniques": {"configured": configured_concepts, "items": []},
        "Data Structures": {"configured": configured_ds, "items": []},
    }

    for p in problems:
        meta = p.get("metadata", {})
        fpath = p.get("file_path", "")
        rel_p = p.get("rel_path", fpath)

        # Platform
        raw_plat = meta.get("platform") or p.get("platform")
        if raw_plat and str(raw_plat).strip():
            fields_data["Platform"]["items"].append((str(raw_plat).strip(), rel_p, fpath))

        # Category
        raw_cat = meta.get("category") or p.get("category")
        if raw_cat and str(raw_cat).strip():
            fields_data["Category"]["items"].append((str(raw_cat).strip(), rel_p, fpath))

        # Tags (split tokens)
        raw_tags = meta.get("tags", "")
        if raw_tags and str(raw_tags).strip():
            for t in str(raw_tags).split(","):
                clean_t = t.strip()
                if clean_t:
                    fields_data["Tags"]["items"].append((clean_t, rel_p, fpath))

        # Concepts
        raw_concepts = meta.get("concepts", "")
        if raw_concepts and str(raw_concepts).strip():
            for c in str(raw_concepts).split(","):
                clean_c = c.strip()
                if clean_c:
                    fields_data["Concepts / Techniques"]["items"].append((clean_c, rel_p, fpath))

        # Data Structures
        raw_ds = meta.get("data_structures", "")
        if raw_ds and str(raw_ds).strip():
            for d in str(raw_ds).split(","):
                clean_d = d.strip()
                if clean_d:
                    fields_data["Data Structures"]["items"].append((clean_d, rel_p, fpath))

    all_affected_files: Set[str] = set()
    duplicate_groups: List[Dict[str, Any]] = []

    for field_name, f_info in fields_data.items():
        conf_list = f_info["configured"]
        discovered_tuples = f_info["items"]
        discovered_values = [item[0] for item in discovered_tuples]

        canon_map = build_canonical_mapping(conf_list, discovered_values)

        # Group discovered tuples by norm_key
        grouped: Dict[str, Dict[str, Set[str]]] = {}
        for raw_val, rel_p, _abs_p in discovered_tuples:
            norm_k = normalize_metadata_key(raw_val)
            if not norm_k:
                continue
            if norm_k not in grouped:
                grouped[norm_k] = {}
            if raw_val not in grouped[norm_k]:
                grouped[norm_k][raw_val] = set()
            grouped[norm_k][raw_val].add(rel_p)

        for norm_k, variant_dict in grouped.items():
            canon_val = canon_map.get(norm_k, list(variant_dict.keys())[0])
            distinct_variants = list(variant_dict.keys())

            # Check if there is duplication or non-canonical casing/spacing in the repository
            has_variation = len(distinct_variants) > 1 or any(v != canon_val for v in distinct_variants)

            if has_variation:
                group_affected_files: Set[str] = set()
                variants_list = []
                for v in sorted(distinct_variants):
                    files_for_v = sorted(list(variant_dict[v]))
                    is_canonical = (v == canon_val)
                    if not is_canonical:
                        group_affected_files.update(files_for_v)
                        all_affected_files.update(files_for_v)
                    variants_list.append({
                        "variant": v,
                        "count": len(files_for_v),
                        "is_canonical": is_canonical,
                        "files": files_for_v,
                    })

                duplicate_groups.append({
                    "field": field_name,
                    "normalized_key": norm_k,
                    "canonical_value": canon_val,
                    "variants": variants_list,
                    "affected_files": sorted(list(group_affected_files)),
                    "total_occurrences": sum(v["count"] for v in variants_list),
                })

    # Also detect physical category folder duplicates if any
    folder_dups: List[Dict[str, Any]] = []
    try:
        top_dirs = [d for d in resolved_repo.iterdir() if d.is_dir() and not d.name.startswith(".") and d.name not in SCAN_EXCLUDE_DIRS]
        dir_grouped: Dict[str, List[str]] = {}
        for d in top_dirs:
            norm_k = normalize_metadata_key(d.name)
            dir_grouped.setdefault(norm_k, []).append(d.name)
        for norm_k, d_names in dir_grouped.items():
            if len(d_names) > 1:
                folder_dups.append({
                    "normalized_key": norm_k,
                    "folder_variants": sorted(d_names),
                })
    except Exception:
        pass

    return {
        "success": True,
        "repo_path": str(resolved_repo),
        "has_duplicates": len(duplicate_groups) > 0 or len(folder_dups) > 0,
        "total_duplicate_groups": len(duplicate_groups),
        "total_affected_files": len(all_affected_files),
        "duplicate_groups": duplicate_groups,
        "category_folder_duplicates": folder_dups,
    }


def normalize_repository_metadata(
    repo_path: "str | Path",
    target_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Explicitly normalize and deduplicate metadata in affected problem source files.

    Safety Guarantees:
    - User-confirmed operation only (never runs silently on search or ordinary scan).
    - Preserves user solution code byte-for-byte unchanged.
    - Preserves problem description, timestamps, and filenames.
    - Updates only the metadata header comments in affected files to their canonical representation.
    - Performs atomic verification on each modified file.
    """
    dup_res = detect_metadata_duplicates(repo_path)
    if not dup_res.get("success"):
        return {
            "success": False,
            "error": dup_res.get("error", "Failed to inspect repository duplicates"),
            "normalized_files_count": 0,
            "updated_files": [],
            "errors": [],
        }

    resolved_repo = Path(repo_path).resolve()
    scan_res = scan_repository(resolved_repo)
    problems = scan_res.get("problems", [])

    # Build canonical maps for each field
    configured_platforms = get_all_platforms()
    configured_categories = get_categories()
    configured_tags = get_all_tags()
    configured_concepts = list(BUILTIN_CONCEPTS)
    configured_ds = list(BUILTIN_DATA_STRUCTURES)

    plat_discovered = [p.get("platform", "") for p in problems if p.get("platform")]
    cat_discovered = [p.get("category", "") for p in problems if p.get("category")]
    tags_discovered = []
    concepts_discovered = []
    ds_discovered = []
    for p in problems:
        meta = p.get("metadata", {})
        for t in str(meta.get("tags", "")).split(","):
            if t.strip():
                tags_discovered.append(t.strip())
        for c in str(meta.get("concepts", "")).split(","):
            if c.strip():
                concepts_discovered.append(c.strip())
        for d in str(meta.get("data_structures", "")).split(","):
            if d.strip():
                ds_discovered.append(d.strip())

    plat_map = build_canonical_mapping(configured_platforms, plat_discovered)
    cat_map = build_canonical_mapping(configured_categories, cat_discovered)
    tag_map = build_canonical_mapping(configured_tags, tags_discovered)
    concept_map = build_canonical_mapping(configured_concepts, concepts_discovered)
    ds_map = build_canonical_mapping(configured_ds, ds_discovered)

    target_keys_set = set(target_keys) if target_keys else None

    updated_files: List[str] = []
    errors: List[str] = []

    for prob in problems:
        file_path = Path(prob["file_path"]).resolve()
        if not file_path.exists():
            continue

        meta = prob.get("metadata", {})
        curr_plat = meta.get("platform") or prob.get("platform", "")
        curr_cat = meta.get("category") or prob.get("category", "")
        curr_tags = meta.get("tags", "")
        curr_concepts = meta.get("concepts", "")
        curr_ds = meta.get("data_structures", "")

        # Canonicalize each field
        new_plat = canonicalize_value(curr_plat, plat_map) if curr_plat else curr_plat
        new_cat = canonicalize_value(curr_cat, cat_map) if curr_cat else curr_cat
        _, new_tags = canonicalize_token_list(curr_tags, tag_map)
        _, new_concepts = canonicalize_token_list(curr_concepts, concept_map)
        _, new_ds = canonicalize_token_list(curr_ds, ds_map)

        # Check if anything changed
        changed = False
        if curr_plat != new_plat and (target_keys_set is None or normalize_metadata_key(curr_plat) in target_keys_set):
            changed = True
        else:
            new_plat = curr_plat

        if curr_cat != new_cat and (target_keys_set is None or normalize_metadata_key(curr_cat) in target_keys_set):
            changed = True
        else:
            new_cat = curr_cat

        if curr_tags != new_tags and (target_keys_set is None or any(normalize_metadata_key(t) in target_keys_set for t in curr_tags.split(","))):
            changed = True
        else:
            new_tags = curr_tags

        if curr_concepts != new_concepts and (target_keys_set is None or any(normalize_metadata_key(c) in target_keys_set for c in curr_concepts.split(","))):
            changed = True
        else:
            new_concepts = curr_concepts

        if curr_ds != new_ds and (target_keys_set is None or any(normalize_metadata_key(d) in target_keys_set for d in curr_ds.split(","))):
            changed = True
        else:
            new_ds = curr_ds

        if changed:
            updated_fields = {
                "title": meta.get("title") or prob.get("title"),
                "platform": new_plat,
                "language": meta.get("language") or prob.get("language"),
                "category": new_cat,
                "concepts": new_concepts,
                "data_structures": new_ds,
                "tags": new_tags,
                "importance": meta.get("importance", "3"),
                "time_complexity": meta.get("time_complexity"),
                "space_complexity": meta.get("space_complexity"),
                "added_date": meta.get("added_date"),
                "description": meta.get("description", ""),
            }

            ok, msg = update_problem_metadata(file_path, updated_fields, repo_path=resolved_repo)
            if ok:
                updated_files.append(str(prob.get("rel_path", file_path.name)))
            else:
                errors.append(f"{prob.get('rel_path', file_path.name)}: {msg}")

    return {
        "success": len(errors) == 0,
        "normalized_files_count": len(updated_files),
        "updated_files": updated_files,
        "errors": errors,
    }


# ==============================================================================
# Phase 5A: Home Dashboard Statistics & Metrics
# ==============================================================================

def parse_date_safely(date_val: Any) -> Optional[date]:
    """
    Safely parse various date representations into a datetime.date object.

    Supports:
    - ISO 8601 (YYYY-MM-DD)
    - Slash/Dot/Dash variations (YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY, MM/DD/YYYY)
    - Word formats ('September 26, 2026', 'Sep 26, 2026', '26 September 2026')
    - Timestamp strings ('YYYY-MM-DD HH:MM:SS')
    - datetime / date instances directly

    Returns None if unparseable, invalid, or empty. Never raises exceptions.
    """
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val

    val_str = str(date_val).strip()
    if not val_str:
        return None

    # Fast-path ISO format (e.g. 2026-09-26)
    try:
        return date.fromisoformat(val_str)
    except (ValueError, TypeError):
        pass

    # Common format candidates
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except (ValueError, TypeError):
            pass

    # Regex search for embedded YYYY-MM-DD or YYYY/MM/DD
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", val_str)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except (ValueError, TypeError):
            pass

    return None


def calculate_streak(active_dates: Set[date], today: Optional[date] = None) -> Tuple[int, int]:
    """
    Calculate (current_streak, longest_streak) from a set of active calendar dates.

    Rules:
    - Active day: At least one problem file has a valid Added date on that day.
    - Multiple problems on one day count as a single active day.
    - Current streak:
        * If today has activity -> count backwards consecutive days starting from today.
        * If today has no activity but yesterday has activity -> count backwards starting from yesterday.
        * If neither today nor yesterday has activity -> current streak is 0.
    - Longest streak:
        * Longest consecutive sequence of active calendar days across all recorded problems.
        * If active_dates is empty -> longest streak is 0.
    """
    if not active_dates:
        return 0, 0

    if today is None:
        today = date.today()

    # Current streak calculation
    cur_streak = 0
    if today in active_dates:
        cur_day = today
        while cur_day in active_dates:
            cur_streak += 1
            cur_day -= timedelta(days=1)
    elif (today - timedelta(days=1)) in active_dates:
        cur_day = today - timedelta(days=1)
        while cur_day in active_dates:
            cur_streak += 1
            cur_day -= timedelta(days=1)
    else:
        cur_streak = 0

    # Longest streak calculation
    sorted_dates = sorted(active_dates)
    longest_streak = 0
    running_seq = 0
    prev_date: Optional[date] = None

    for d in sorted_dates:
        if prev_date is None:
            running_seq = 1
        elif d == prev_date + timedelta(days=1):
            running_seq += 1
        elif d == prev_date:
            pass
        else:
            running_seq = 1

        if running_seq > longest_streak:
            longest_streak = running_seq
        prev_date = d

    return cur_streak, longest_streak


def _generate_heatmap_data(activity_by_date: Dict[str, int], today: date) -> List[List[Dict[str, Any]]]:
    """
    Generate 12 weeks of 7-day cells (Monday -> Sunday) for the activity heatmap.
    """
    # Current week's Monday & Sunday
    monday_current = today - timedelta(days=today.weekday())
    
    # 12 weeks window starting 11 weeks prior to the current week's Monday
    start_monday = monday_current - timedelta(weeks=11)

    weeks: List[List[Dict[str, Any]]] = []

    for w in range(12):
        week_days = []
        for d_idx in range(7):
            day_date = start_monday + timedelta(days=(w * 7 + d_idx))
            iso_key = day_date.isoformat()
            cnt = activity_by_date.get(iso_key, 0)

            # Part 2: Exact intensity levels
            # 0 -> 0 (empty), 1 -> 1, 2 -> 2, 3+ -> 3
            if cnt == 0:
                level = 0
            elif cnt == 1:
                level = 1
            elif cnt == 2:
                level = 2
            else:
                level = 3

            week_days.append({
                "date": iso_key,
                "formatted_date": day_date.strftime("%B %d, %Y"),
                "day_name": day_date.strftime("%a"),
                "day_number": day_date.day,
                "month_name": day_date.strftime("%b"),
                "count": cnt,
                "level": level,
                "is_today": day_date == today,
                "is_future": day_date > today,
            })
        weeks.append(week_days)

    return weeks


def _generate_empty_heatmap(today: date) -> List[List[Dict[str, Any]]]:
    """Generate empty 12-week heatmap grid with zero activity."""
    return _generate_heatmap_data({}, today)


def get_dashboard_stats(repo_path: "str | Path", today: Optional[date] = None) -> Dict[str, Any]:
    """
    Calculate and return complete Phase 5A dashboard statistics from the configured repository.

    The repository remains the sole source of truth.
    Performs a single read-only scan of the repository.

    Returns:
        {
            "success": bool,
            "repo_path": str,
            "total_problems": int,
            "this_week": int,
            "this_month": int,
            "current_streak": int,
            "longest_streak": int,
            "category_counts": Dict[str, int],
            "most_practiced_categories": List[Tuple[str, int]],
            "least_practiced_categories": List[Tuple[str, int]],
            "recent_problems": List[Dict[str, Any]],
            "activity_by_date": Dict[str, int],
            "heatmap_weeks": List[List[Dict[str, Any]]],
            "problems": List[Dict[str, Any]],
        }
    """
    if today is None:
        today = date.today()

    is_val, val_msg = validate_repository(repo_path)
    if not is_val:
        return {
            "success": False,
            "error": val_msg,
            "repo_path": str(repo_path) if repo_path else "",
            "total_problems": 0,
            "this_week": 0,
            "this_month": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "category_counts": {},
            "most_practiced_categories": [],
            "least_practiced_categories": [],
            "recent_problems": [],
            "activity_by_date": {},
            "heatmap_weeks": _generate_empty_heatmap(today),
            "problems": [],
        }

    scan_res = scan_repository(repo_path)
    if not scan_res.get("success"):
        return {
            "success": False,
            "error": scan_res.get("error", "Failed to scan repository"),
            "repo_path": str(repo_path),
            "total_problems": 0,
            "this_week": 0,
            "this_month": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "category_counts": {},
            "most_practiced_categories": [],
            "least_practiced_categories": [],
            "recent_problems": [],
            "activity_by_date": {},
            "heatmap_weeks": _generate_empty_heatmap(today),
            "problems": [],
        }

    problems = scan_res.get("problems", [])
    total_problems = len(problems)

    # Week boundary: Monday to Sunday
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    this_week_count = 0
    this_month_count = 0
    activity_by_date: Dict[str, int] = {}
    active_dates: Set[date] = set()
    category_counts: Dict[str, int] = {}
    dated_problems: List[Dict[str, Any]] = []

    # Category Canonical Mapping
    raw_cats = [(prob.get("metadata", {}).get("category") or prob.get("category") or "").strip() for prob in problems]
    all_configured_categories = get_categories()
    cat_map = build_canonical_mapping(all_configured_categories, raw_cats)

    for prob in problems:
        meta = prob.get("metadata", {})
        raw_added = meta.get("added_date") or ""
        parsed_dt = parse_date_safely(raw_added)

        # Primary Category count (only from Primary Category metadata, canonicalized)
        cat = (meta.get("category") or prob.get("category") or "").strip()
        if cat:
            canonical_cat = cat_map.get(normalize_metadata_key(cat), normalize_metadata_display(cat))
            category_counts[canonical_cat] = category_counts.get(canonical_cat, 0) + 1

        if parsed_dt is not None:
            # Week count (Monday through Sunday)
            if start_of_week <= parsed_dt <= end_of_week:
                this_week_count += 1

            # Month count (Calendar month of today)
            if parsed_dt.year == today.year and parsed_dt.month == today.month:
                this_month_count += 1

            iso_key = parsed_dt.isoformat()
            activity_by_date[iso_key] = activity_by_date.get(iso_key, 0) + 1
            active_dates.add(parsed_dt)

            formatted_dt_str = parsed_dt.strftime("%B %d, %Y")
        else:
            formatted_dt_str = raw_added.strip()

        display_cat = cat or prob.get("folder_category") or "Uncategorized"

        dated_problems.append({
            "title": prob.get("title", ""),
            "category": display_cat,
            "platform": prob.get("platform") or meta.get("platform", ""),
            "language": prob.get("language") or meta.get("language", ""),
            "added_date": raw_added,
            "parsed_date": parsed_dt,
            "formatted_date": formatted_dt_str,
            "file_path": prob.get("file_path", ""),
            "rel_path": prob.get("rel_path", ""),
            "status": prob.get("status", "incomplete"),
        })

    # Calculate streaks
    cur_streak, long_streak = calculate_streak(active_dates, today)

    # Categories sorted descending by count, with alphabetical tie-breaker
    sorted_cats_desc = sorted(category_counts.items(), key=lambda x: (-x[1], x[0].lower()))
    most_practiced = sorted_cats_desc[:3]

    # Categories sorted ascending by count for less practiced
    sorted_cats_asc = sorted(category_counts.items(), key=lambda x: (x[1], x[0].lower()))
    least_practiced = sorted_cats_asc[:3]

    # Recent problems: sorted newest first, deterministic tie-breaker on title
    def recent_sort_key(p: Dict[str, Any]) -> Tuple[int, int, str]:
        dt = p["parsed_date"]
        has_date = 1 if dt is not None else 0
        date_ordinal = dt.toordinal() if dt is not None else 0
        return (has_date, date_ordinal, p["title"].lower())

    dated_problems.sort(key=recent_sort_key, reverse=True)
    recent_problems = dated_problems[:10]

    # Activity Heatmap Data
    heatmap_weeks = _generate_heatmap_data(activity_by_date, today)

    return {
        "success": True,
        "repo_path": scan_res.get("repo_path", ""),
        "total_problems": total_problems,
        "this_week": this_week_count,
        "this_month": this_month_count,
        "current_streak": cur_streak,
        "longest_streak": long_streak,
        "category_counts": category_counts,
        "most_practiced_categories": most_practiced,
        "least_practiced_categories": least_practiced,
        "recent_problems": recent_problems,
        "activity_by_date": activity_by_date,
        "heatmap_weeks": heatmap_weeks,
        "problems": problems,
    }


def normalize_problem_record(prob: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a single normalized internal problem record for Search, Topic View, and filtering.
    Guarantees consistent data representation across all search, filtering, and view operations.
    """
    meta = prob.get("metadata", {})
    file_path_str = prob.get("file_path", "")
    target_path = Path(file_path_str) if file_path_str else None

    # Title: metadata title -> prob title -> file stem
    title = (prob.get("title") or meta.get("title") or (target_path.stem if target_path else "")).strip()

    # Platform: stripped clean
    platform = (prob.get("platform") or meta.get("platform") or "").strip()

    # Language: stripped clean, default by extension if empty
    ext = target_path.suffix.lower() if target_path else ""
    default_lang = "C++" if ext == ".cpp" else ("Java" if ext == ".java" else ("Python" if ext == ".py" else ""))
    language = (prob.get("language") or meta.get("language") or default_lang).strip()

    # Primary Category: Metadata category is authoritative; fallback to folder category or Uncategorized
    category = (meta.get("category") or prob.get("category") or prob.get("folder_category") or "Uncategorized").strip()
    folder_category = (prob.get("folder_category") or "").strip()

    # Tokenized fields: Tags, Concepts / Techniques, Data Structures
    raw_tags = (meta.get("tags") or "").strip()
    tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []

    raw_concepts = (meta.get("concepts") or "").strip()
    concepts_list = [c.strip() for c in raw_concepts.split(",") if c.strip()] if raw_concepts else []

    raw_ds = (meta.get("data_structures") or "").strip()
    ds_list = [d.strip() for d in raw_ds.split(",") if d.strip()] if raw_ds else []

    # Importance: normalized 1-5 digit
    raw_imp = str(meta.get("importance", "")).strip()
    imp_dig = re.search(r"[1-5]", raw_imp)
    importance = imp_dig.group(0) if imp_dig else raw_imp

    # Complexities & Dates
    tc = (meta.get("time_complexity") or "").strip()
    sc = (meta.get("space_complexity") or "").strip()
    added_date = (meta.get("added_date") or "").strip()
    description = (meta.get("description") or "").strip()
    rel_path = str(prob.get("rel_path", ""))

    return {
        "title": title,
        "platform": platform,
        "language": language,
        "category": category,
        "folder_category": folder_category,
        "concepts": raw_concepts,
        "concepts_list": concepts_list,
        "data_structures": raw_ds,
        "data_structures_list": ds_list,
        "tags": raw_tags,
        "tags_list": tags_list,
        "importance": importance,
        "time_complexity": tc,
        "space_complexity": sc,
        "added_date": added_date,
        "description": description,
        "file_path": str(file_path_str),
        "rel_path": rel_path,
        "status": prob.get("status", "complete"),
        "is_complete": prob.get("is_complete", True),
    }


# ==============================================================================
# Phase 7: Topic / Category View
# ==============================================================================

def get_category_view(
    repo_path: "str | Path",
    category: str,
) -> Dict[str, Any]:
    """
    Get structured category view data for a specified Primary Category.

    Reuses the single-source-of-truth scanner and normalizer.
    Matches problems based strictly on their authoritative Primary Category metadata.

    Returns:
        {
            "success": bool,
            "category": str,                    # Canonical display name
            "problem_count": int,
            "platform_counts": Dict[str, int], # e.g. {"Smart Interview": 4, "LeetCode": 1}
            "language_counts": Dict[str, int], # e.g. {"C++": 5}
            "latest_added": Optional[str],     # Formatted date string (e.g. "September 26, 2026") or None
            "problems": List[Dict[str, Any]],  # Normalized problem records, sorted newest first
            "error": Optional[str],
        }
    """
    is_val, val_msg = validate_repository(repo_path)
    if not is_val:
        return {
            "success": False,
            "category": category,
            "problem_count": 0,
            "platform_counts": {},
            "language_counts": {},
            "latest_added": None,
            "problems": [],
            "error": val_msg,
        }

    scan_res = scan_repository(repo_path)
    if not scan_res.get("success"):
        return {
            "success": False,
            "category": category,
            "problem_count": 0,
            "platform_counts": {},
            "language_counts": {},
            "latest_added": None,
            "problems": [],
            "error": scan_res.get("error", "Failed to scan repository"),
        }

    raw_problems = scan_res.get("problems", [])
    normalized_problems = [normalize_problem_record(p) for p in raw_problems]

    # Category Canonical Mapping
    repo_categories = [p["category"] for p in normalized_problems if p["category"]]
    all_configured_categories = get_categories()
    cat_map = build_canonical_mapping(all_configured_categories, repo_categories)

    target_cat_key = normalize_metadata_key(category)
    if not target_cat_key:
        canonical_cat_name = "Uncategorized"
        target_cat_key = normalize_metadata_key("Uncategorized")
    else:
        canonical_cat_name = cat_map.get(target_cat_key, normalize_metadata_display(category))

    # Platform Canonical Mapping
    repo_platforms = [p["platform"] for p in normalized_problems if p["platform"]]
    all_configured_platforms = list(BUILTIN_PLATFORMS) + get_custom_platforms() + ["Other"]
    plat_map = build_canonical_mapping(all_configured_platforms, repo_platforms)

    # Filter problems belonging to this canonical category (Primary Category is authoritative)
    matching_problems: List[Dict[str, Any]] = []
    for prob in normalized_problems:
        prob_cat = prob.get("category", "")
        if normalize_metadata_key(prob_cat) == target_cat_key:
            matching_problems.append(prob)

    # Sort newest first using Added metadata date, with deterministic secondary ordering on title
    def problem_sort_key(p: Dict[str, Any]) -> Tuple[int, int, str]:
        raw_dt = p.get("added_date", "")
        dt = parse_date_safely(raw_dt)
        has_date = 0 if dt is not None else 1
        date_ordinal = -dt.toordinal() if dt is not None else 0
        return (has_date, date_ordinal, p.get("title", "").lower())

    matching_problems.sort(key=problem_sort_key)

    # Calculate statistics
    platform_counts: Dict[str, int] = {}
    for p in matching_problems:
        raw_plat = p.get("platform", "")
        if raw_plat:
            plat_key = normalize_metadata_key(raw_plat)
            canonical_plat = plat_map.get(plat_key, normalize_metadata_display(raw_plat))
            platform_counts[canonical_plat] = platform_counts.get(canonical_plat, 0) + 1

    language_counts: Dict[str, int] = {}
    for p in matching_problems:
        raw_lang = p.get("language", "")
        if raw_lang:
            lang_display = raw_lang.strip()
            language_counts[lang_display] = language_counts.get(lang_display, 0) + 1

    # Format Latest Added Date
    latest_added = None
    for p in matching_problems:
        dt = parse_date_safely(p.get("added_date", ""))
        if dt is not None:
            latest_added = dt.strftime("%B %d, %Y")
            break
        elif p.get("added_date", "").strip() and not latest_added:
            latest_added = p.get("added_date", "").strip()

    return {
        "success": True,
        "category": canonical_cat_name,
        "problem_count": len(matching_problems),
        "platform_counts": platform_counts,
        "language_counts": language_counts,
        "latest_added": latest_added,
        "problems": matching_problems,
        "error": None,
    }


def search_problems(
    repo_path: "str | Path",
    query: str = "",
    category: str = "",
    platform: str = "",
    language: str = "",
    tags: str = "",
    concepts: str = "",
    data_structures: str = "",
    importance: "str | int" = "",
) -> Dict[str, Any]:
    """
    Search and filter repository DSA problems strictly across structured header metadata.

    Single Source of Truth:
    - Normalizes every problem record through normalize_problem_record.
    - Derives available filter options directly from the repository records + config.
    - Searches exclusively across structured metadata fields; does NOT inspect solution code.
    - Supports token-based matching for Tags, Concepts, and Data Structures.
    """
    scan_res = scan_repository(repo_path)
    if not scan_res.get("success"):
        return {
            "success": False,
            "error": scan_res.get("error", "Failed to scan repository"),
            "total_matching": 0,
            "total_repository": 0,
            "results": [],
            "category_counts": {},
            "filter_options": {
                "categories": ["Uncategorized"],
                "platforms": list(BUILTIN_PLATFORMS) + ["Other"],
                "languages": ["C++", "Java", "Python"],
                "tags": [],
                "concepts": [],
                "data_structures": [],
            },
        }

    raw_problems = scan_res.get("problems", [])
    normalized_problems = [normalize_problem_record(p) for p in raw_problems]

    # Build dynamic filter options from repository records + configuration using canonical mapping
    repo_platforms = [p["platform"] for p in normalized_problems if p["platform"]]
    all_configured_platforms = list(BUILTIN_PLATFORMS) + get_custom_platforms() + ["Other"]
    plat_map = build_canonical_mapping(all_configured_platforms, repo_platforms)
    
    seen_plat_keys = set()
    filter_platforms = []
    for p in all_configured_platforms + repo_platforms:
        norm_k = normalize_metadata_key(p)
        if norm_k and norm_k not in seen_plat_keys:
            seen_plat_keys.add(norm_k)
            filter_platforms.append(plat_map.get(norm_k, normalize_metadata_display(p)))

    repo_categories = [p["category"] for p in normalized_problems if p["category"]]
    all_configured_categories = get_categories()
    cat_map = build_canonical_mapping(all_configured_categories, repo_categories)

    seen_cat_keys = set()
    filter_categories = []
    for c in all_configured_categories + repo_categories:
        norm_k = normalize_metadata_key(c)
        if norm_k and norm_k not in seen_cat_keys:
            seen_cat_keys.add(norm_k)
            filter_categories.append(cat_map.get(norm_k, normalize_metadata_display(c)))
    filter_categories.sort(key=lambda x: (x == "Uncategorized", x.lower()))

    repo_languages = {p["language"] for p in normalized_problems if p["language"]}
    all_languages = ["C++", "Java", "Python"] + [l for l in repo_languages if l not in ("C++", "Java", "Python")]
    filter_languages = sorted(list(set(all_languages)), key=lambda x: (x not in ("C++", "Java", "Python"), x))

    repo_tags = []
    for p in normalized_problems:
        repo_tags.extend(p["tags_list"])
    tag_map = build_canonical_mapping(get_all_tags(), repo_tags)
    filter_tags = sorted(list({tag_map.get(normalize_metadata_key(t), normalize_metadata_display(t)) for t in repo_tags if normalize_metadata_key(t)}), key=lambda x: x.lower())

    repo_concepts = []
    for p in normalized_problems:
        repo_concepts.extend(p["concepts_list"])
    concept_map = build_canonical_mapping(BUILTIN_CONCEPTS, repo_concepts)
    filter_concepts = sorted(list({concept_map.get(normalize_metadata_key(c), normalize_metadata_display(c)) for c in repo_concepts if normalize_metadata_key(c)}), key=lambda x: x.lower())

    repo_ds = []
    for p in normalized_problems:
        repo_ds.extend(p["data_structures_list"])
    ds_map = build_canonical_mapping(BUILTIN_DATA_STRUCTURES, repo_ds)
    filter_ds = sorted(list({ds_map.get(normalize_metadata_key(d), normalize_metadata_display(d)) for d in repo_ds if normalize_metadata_key(d)}), key=lambda x: x.lower())

    # Normalization of input filters
    q_lower = query.strip().lower()
    f_cat_key = normalize_metadata_key(category)
    f_plat_key = normalize_metadata_key(platform)
    f_lang_key = normalize_metadata_key(language)
    f_tags_key = normalize_metadata_key(tags)
    f_conc_key = normalize_metadata_key(concepts)
    f_ds_key = normalize_metadata_key(data_structures)
    f_imp = str(importance).strip()

    matching_results: List[Dict[str, Any]] = []
    category_counts: Dict[str, int] = {}

    for rec in normalized_problems:
        # 1. Apply structured text query (searches ONLY structured header metadata)
        if q_lower:
            searchable_metadata = (
                f"{rec['title']} {rec['category']} {rec['platform']} {rec['language']} "
                f"{rec['concepts']} {rec['data_structures']} {rec['tags']} {rec['importance']} "
                f"{rec['time_complexity']} {rec['space_complexity']} {rec['added_date']} {rec['description']}"
            ).lower()
            if q_lower not in searchable_metadata:
                continue

        # 2. Apply Category filter (Primary Category is authoritative, normalized match)
        if f_cat_key and f_cat_key not in ("all", "all categories"):
            if normalize_metadata_key(rec["category"]) != f_cat_key and normalize_metadata_key(rec["folder_category"]) != f_cat_key:
                continue

        # 3. Apply Platform filter (normalized match)
        if f_plat_key and f_plat_key not in ("all", "all platforms"):
            if normalize_metadata_key(rec["platform"]) != f_plat_key:
                continue

        # 4. Apply Language filter (normalized match)
        if f_lang_key and f_lang_key not in ("all", "all languages"):
            if normalize_metadata_key(rec["language"]) != f_lang_key:
                continue

        # 5. Apply Tags filter (token-based normalized match)
        if f_tags_key and f_tags_key not in ("all", "all tags"):
            if not any(f_tags_key == normalize_metadata_key(t) or f_tags_key in normalize_metadata_key(t) for t in rec["tags_list"]):
                continue

        # 6. Apply Concepts filter (token-based normalized match)
        if f_conc_key and f_conc_key not in ("all", "all concepts"):
            if not any(f_conc_key == normalize_metadata_key(c) or f_conc_key in normalize_metadata_key(c) for c in rec["concepts_list"]):
                continue

        # 7. Apply Data Structures filter (token-based normalized match)
        if f_ds_key and f_ds_key not in ("all", "all data structures"):
            if not any(f_ds_key == normalize_metadata_key(d) or f_ds_key in normalize_metadata_key(d) for d in rec["data_structures_list"]):
                continue

        # 8. Apply Importance filter
        if f_imp and f_imp.lower() != "all":
            imp_dig_match = re.search(r"[1-5]", f_imp)
            target_dig = imp_dig_match.group(0) if imp_dig_match else f_imp
            if rec["importance"] != target_dig:
                continue

        # Passed all filters
        matching_results.append(rec)

        # Count category for category browser using canonical display representation
        cat_disp = cat_map.get(normalize_metadata_key(rec["category"]), rec["category"])
        category_counts[cat_disp] = category_counts.get(cat_disp, 0) + 1

    return {
        "success": True,
        "total_matching": len(matching_results),
        "total_repository": len(normalized_problems),
        "results": matching_results,
        "category_counts": category_counts,
        "filter_options": {
            "categories": filter_categories,
            "platforms": filter_platforms,
            "languages": filter_languages,
            "tags": filter_tags,
            "concepts": filter_concepts,
            "data_structures": filter_ds,
        },
    }


def is_vscode_available() -> Tuple[bool, str]:
    """Check if VS Code 'code' command is available on system PATH."""
    code_path = shutil.which("code")
    if code_path:
        return True, f"VS Code found at {code_path}"
    code_cmd = shutil.which("code.cmd")
    if code_cmd:
        return True, f"VS Code found at {code_cmd}"
    return False, "VS Code command 'code' was not found on PATH."


def validate_file_for_open(repo_path: "str | Path", file_path: "str | Path") -> Tuple[bool, str, Optional[Path]]:
    """
    Validate that a file exists, is strictly inside the configured repository, and has a supported extension.
    Safety guarantees:
    1. Rejects missing or non-file paths.
    2. Enforces path traversal guard against configured repository root (if repo_path provided).
    3. Rejects unsupported extensions (only .cpp, .java, and .py allowed).
    """
    if not file_path:
        return False, "File path is required.", None

    target = Path(file_path).resolve()

    if not target.exists() or not target.is_file():
        return False, f"File no longer exists: {target.name}\nRun Rescan Repository to refresh the index.", None

    # Path traversal protection: target must be inside configured repository
    if repo_path:
        resolved_repo = Path(repo_path).resolve()
        try:
            target.relative_to(resolved_repo)
        except ValueError:
            return False, f"Security restriction: File '{target}' is outside the configured repository.", None

    if target.suffix.lower() not in RECOGNIZED_EXTENSIONS:
        return False, f"Unsupported file extension '{target.suffix}'. Only .cpp, .java, and .py files can be opened.", None

    return True, "File valid.", target


def open_file_with_system(file_path: "str | Path", repo_path: Optional["str | Path"] = None) -> Tuple[bool, str]:
    """
    Safely open a validated DSA problem source file using the Windows Open With / system associated application flow.

    Does not hardcode VS Code, PyCharm, CLion, or any specific editor.
    Invokes the native operating system application association / Open With mechanism.
    """
    is_val, val_msg, valid_path = validate_file_for_open(repo_path or "", file_path)
    if not is_val or not valid_path:
        return False, val_msg

    try:
        if sys.platform == "win32":
            # On Windows, trigger native Open With dialog via shell32.dll OpenAs_RunDLL
            # If that fails or is unavailable, fallback to os.startfile
            try:
                subprocess.Popen(["rundll32.exe", "shell32.dll,OpenAs_RunDLL", str(valid_path)], shell=False)
                return True, f"Triggered Open With for {valid_path.name}."
            except Exception:
                os.startfile(str(valid_path))
                return True, f"Opened {valid_path.name} with default application."
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(valid_path)], shell=False)
            return True, f"Opened {valid_path.name}."
        else:
            subprocess.Popen(["xdg-open", str(valid_path)], shell=False)
            return True, f"Opened {valid_path.name}."
    except Exception as exc:
        return False, f"Failed to open file: {exc}"


def open_in_vscode(file_path: "str | Path", repo_path: Optional["str | Path"] = None) -> Tuple[bool, str]:
    """
    Safely open a validated DSA source file in VS Code if available (kept for backward compatibility).
    """
    is_val, val_msg, valid_path = validate_file_for_open(repo_path or "", file_path)
    if not is_val or not valid_path:
        return False, val_msg

    is_avail, avail_msg = is_vscode_available()
    if not is_avail:
        return False, f"VS Code was not found on PATH.\n\nYou can open the file manually:\n{valid_path}"

    try:
        subprocess.Popen(["code", str(valid_path)], shell=False)
        return True, f"Opened {valid_path.name} in VS Code."
    except Exception as exc:
        return False, f"Failed to launch VS Code: {exc}"



