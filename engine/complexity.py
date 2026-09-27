"""
complexity.py - Static complexity analyzer for Python, C++, and Java solution code.

Provides language-aware analysis for Time Complexity and Space Complexity.
Uses Python AST for Python solutions and structural/token analysis for C++ and Java.
Returns 'Unable to determine' when the complexity cannot be established with confidence.
"""

import ast
import re
from typing import Dict, List, Optional, Set, Tuple


class ComplexityResult:
    def __init__(self, time_complexity: str, space_complexity: str) -> None:
        self.time_complexity = time_complexity
        self.space_complexity = space_complexity

    def to_dict(self) -> Dict[str, str]:
        return {
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
        }


# ==============================================================================
# PYTHON ANALYZER (AST-BASED)
# ==============================================================================

class PythonComplexityAnalyzer:
    def analyze(self, code: str) -> ComplexityResult:
        code_clean = code.strip()
        if not code_clean:
            return ComplexityResult("Unable to determine", "Unable to determine")

        try:
            tree = ast.parse(code_clean)
        except SyntaxError:
            return ComplexityResult("Unable to determine", "Unable to determine")

        # 1. Analyze Sorting
        has_sort = self._detect_sort(tree)

        # 2. Analyze Recursion
        is_recursive, rec_type, rec_branching = self._detect_recursion(tree)

        # 3. Analyze Loops & Binary Search
        loop_depth, has_binary_search = self._analyze_loops(tree)

        # 4. Determine Time Complexity
        time_comp = self._derive_time_complexity(
            loop_depth=loop_depth,
            has_sort=has_sort,
            has_binary_search=has_binary_search,
            is_recursive=is_recursive,
            rec_type=rec_type,
            rec_branching=rec_branching,
        )

        # 5. Determine Space Complexity
        space_comp = self._derive_space_complexity(
            tree=tree,
            is_recursive=is_recursive,
            rec_type=rec_type,
        )

        return ComplexityResult(time_comp, space_comp)

    def _detect_sort(self, tree: ast.AST) -> bool:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "sorted":
                    return True
                if isinstance(node.func, ast.Attribute) and node.func.attr == "sort":
                    return True
        return False

    def _detect_recursion(self, tree: ast.AST) -> Tuple[bool, str, int]:
        """
        Check if any function calls itself.
        Returns (is_recursive, rec_type, branching_factor)
        rec_type: 'divide_and_conquer', 'linear', 'exponential'
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                fn_name = node.name
                calls_to_self: List[ast.Call] = []
                has_halving = False

                for inner in ast.walk(node):
                    if isinstance(inner, ast.Call):
                        if isinstance(inner.func, ast.Name) and inner.func.id == fn_name:
                            calls_to_self.append(inner)
                            # Inspect arguments for halving (// 2 or / 2)
                            for arg in inner.args:
                                for arg_sub in ast.walk(arg):
                                    if isinstance(arg_sub, (ast.FloorDiv, ast.Div, ast.RShift)):
                                        has_halving = True

                count = len(calls_to_self)
                if count > 0:
                    if has_halving:
                        return True, "divide_and_conquer", count
                    if count >= 2:
                        return True, "exponential", count
                    return True, "linear", count

        return False, "none", 0

    def _is_binary_search_while(self, node: ast.While) -> bool:
        """Heuristic check if a while loop is binary search."""
        # 1. Condition often compares two bounds: low <= high, left < right, etc.
        has_comparison = isinstance(node.test, ast.Compare)
        # 2. Body modifies mid = (low + high) // 2 or updates bounds with mid + 1, mid - 1
        has_mid_calc = False
        has_bound_update = False

        for sub in ast.walk(node):
            if isinstance(sub, ast.BinOp):
                if isinstance(sub.op, (ast.FloorDiv, ast.Div, ast.RShift)):
                    has_mid_calc = True
            if isinstance(sub, ast.Assign):
                for target in sub.targets:
                    if isinstance(target, ast.Name) and target.id.lower() in ("mid", "m"):
                        has_mid_calc = True
            if isinstance(sub, ast.Name) and sub.id.lower() in ("low", "high", "left", "right", "start", "end", "l", "r"):
                has_bound_update = True

        return has_comparison and has_mid_calc and has_bound_update

    def _analyze_loops(self, tree: ast.AST) -> Tuple[int, bool]:
        """Returns (max_nesting_depth, has_binary_search)"""
        has_bs = False

        def get_depth(node: ast.AST, current_depth: int) -> int:
            nonlocal has_bs
            max_d = current_depth

            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.While) and self._is_binary_search_while(child):
                    has_bs = True
                    # A binary search loop has logarithmic depth, not standard O(n) loop depth
                    child_depth = get_depth(child, current_depth)
                    max_d = max(max_d, child_depth)
                elif isinstance(child, (ast.For, ast.While)):
                    child_depth = get_depth(child, current_depth + 1)
                    max_d = max(max_d, child_depth)
                else:
                    child_depth = get_depth(child, current_depth)
                    max_d = max(max_d, child_depth)

            return max_d

        max_depth = get_depth(tree, 0)
        return max_depth, has_bs

    def _derive_time_complexity(
        self,
        loop_depth: int,
        has_sort: bool,
        has_binary_search: bool,
        is_recursive: bool,
        rec_type: str,
        rec_branching: int,
    ) -> str:
        # Recursion checks
        if is_recursive:
            if rec_type == "exponential":
                return f"O({rec_branching}^n)" if rec_branching > 1 else "O(2^n)"
            if rec_type == "divide_and_conquer":
                if loop_depth >= 1:
                    return "O(n log n)"
                return "O(log n)"
            if rec_type == "linear":
                return "O(n)"

        # Loop depth + Binary Search / Sort
        if loop_depth == 0:
            if has_binary_search:
                return "O(log n)"
            if has_sort:
                return "O(n log n)"
            return "O(1)"

        if loop_depth == 1:
            if has_binary_search:
                return "O(n log n)"
            if has_sort:
                return "O(n² log n)"
            return "O(n)"

        if loop_depth == 2:
            return "O(n²)"

        if loop_depth == 3:
            return "O(n³)"

        if loop_depth > 3:
            return f"O(n^{loop_depth})"

        return "Unable to determine"

    def _derive_space_complexity(self, tree: ast.AST, is_recursive: bool, rec_type: str) -> str:
        has_collection = False
        has_grid = False

        for node in ast.walk(tree):
            # Check for dict/hash map, set, or list allocations
            if isinstance(node, (ast.Dict, ast.Set, ast.List)):
                if len(getattr(node, "elts", [])) > 0 or isinstance(node, ast.Dict):
                    has_collection = True
            # Check for dict(), set(), list(), collections.defaultdict, collections.Counter
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in (
                    "dict", "set", "list", "defaultdict", "Counter"
                ):
                    has_collection = True
                if isinstance(node.func, ast.Attribute) and node.func.attr in (
                    "defaultdict", "Counter"
                ):
                    has_collection = True
            # Comprehensions
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
                has_collection = True
                # Check for nested comprehension: [[0]*m for _ in range(n)]
                for gen in node.generators:
                    if isinstance(node, ast.ListComp) and isinstance(node.elt, (ast.List, ast.ListComp, ast.BinOp)):
                        has_grid = True

        if has_grid:
            return "O(n²)"

        if has_collection:
            return "O(n)"

        if is_recursive:
            if rec_type == "divide_and_conquer":
                return "O(log n)"
            return "O(n)"

        return "O(1)"


# ==============================================================================
# C++ & JAVA ANALYZER (STRUCTURAL / PATTERN-BASED)
# ==============================================================================

class CompiledLanguageComplexityAnalyzer:
    """Analyzer for C++ and Java solutions."""

    def __init__(self, language: str) -> None:
        self.language = language

    def analyze(self, code: str) -> ComplexityResult:
        code_clean = self._clean_code(code)
        if not code_clean:
            return ComplexityResult("Unable to determine", "Unable to determine")

        # 1. Detect Sorting
        has_sort = bool(re.search(r"\b(std::sort|sort|Arrays\.sort|Collections\.sort)\s*\(", code_clean))

        # 2. Detect Binary Search
        has_binary_search = self._detect_binary_search(code_clean)

        # 3. Detect Recursion
        is_recursive, rec_type = self._detect_recursion(code_clean)

        # 4. Measure Loop Nesting Depth
        loop_depth = self._measure_loop_depth(code_clean, has_binary_search=has_binary_search)

        # 5. Determine Time Complexity
        time_comp = self._derive_time_complexity(
            loop_depth=loop_depth,
            has_sort=has_sort,
            has_binary_search=has_binary_search,
            is_recursive=is_recursive,
            rec_type=rec_type,
        )

        # 6. Determine Space Complexity
        space_comp = self._derive_space_complexity(
            code_clean=code_clean,
            is_recursive=is_recursive,
            rec_type=rec_type,
        )

        return ComplexityResult(time_comp, space_comp)

    def _clean_code(self, code: str) -> str:
        # Remove single-line comments
        no_line_comments = re.sub(r"//.*", "", code)
        # Remove multi-line comments
        no_comments = re.sub(r"/\*.*?\*/", "", no_line_comments, flags=re.DOTALL)
        # Remove string literals
        no_strings = re.sub(r'"(\\.|[^"\\])*"', '""', no_comments)
        return no_strings.strip()

    def _detect_binary_search(self, code: str) -> bool:
        # Matches while (low <= high), while (left < right), etc.
        while_cond = re.search(r"while\s*\(\s*([a-zA-Z_]\w*)\s*(?:<=|<)\s*([a-zA-Z_]\w*)\s*\)", code)
        if while_cond:
            # Check for mid computation: / 2 or >> 1 or mid =
            has_mid = bool(re.search(r"(?:/|>>)\s*2|\bmid\b", code, re.IGNORECASE))
            if has_mid:
                return True
        return False

    def _detect_recursion(self, code: str) -> Tuple[bool, str]:
        """Heuristic check for recursive method calls."""
        # Find method signature: e.g. int search(...) or void solve(...)
        method_defs = re.findall(
            r"\b(?:[a-zA-Z_]\w*(?:<[^>]+>)?)\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{", code
        )
        for method_name in method_defs:
            if method_name in ("if", "for", "while", "switch", "catch"):
                continue
            # Search for recursive calls to method_name within code
            call_pattern = rf"\b{re.escape(method_name)}\s*\("
            matches = list(re.finditer(call_pattern, code))
            # First match is the definition itself; any subsequent matches are calls
            if len(matches) > 1:
                # Check if divide-and-conquer (passes / 2 or mid - 1 or mid + 1)
                if re.search(r"\bmid\s*[\+\-]\s*1|/\s*2", code):
                    return True, "divide_and_conquer"
                return True, "linear"

        return False, "none"

    def _measure_loop_depth(self, code: str, has_binary_search: bool = False) -> int:
        """
        Track nesting depth of for/while loops using brace balancing and loop keyword scanning.
        """
        code_to_measure = code
        if has_binary_search:
            # Mask out the logarithmic binary search while-statement so it is not counted as an O(n) loop
            code_to_measure = re.sub(
                r"\bwhile\s*\(\s*[a-zA-Z_]\w*\s*(?:<=|<)\s*[a-zA-Z_]\w*\s*\)",
                "/* bs_while */",
                code,
                count=1,
            )

        # Tokenize code into braces and loop keywords
        pattern = re.compile(r"(\bfor\b|\bwhile\b|\{|\})")
        tokens = [m.group(1) for m in pattern.finditer(code_to_measure)]

        max_loop_nesting = 0
        loop_stack: List[int] = []  # Tracks brace depth at which loops started
        current_brace_depth = 0
        pending_loop = False

        for token in tokens:
            if token in ("for", "while"):
                pending_loop = True
            elif token == "{":
                current_brace_depth += 1
                if pending_loop:
                    loop_stack.append(current_brace_depth)
                    max_loop_nesting = max(max_loop_nesting, len(loop_stack))
                    pending_loop = False
            elif token == "}":
                # Close any loops that were scoped at or deeper than this brace depth
                while loop_stack and loop_stack[-1] >= current_brace_depth:
                    loop_stack.pop()
                current_brace_depth = max(0, current_brace_depth - 1)
                pending_loop = False

        # Fallback if loops don't use braces: count simple consecutive for occurrences
        if max_loop_nesting == 0:
            for_count = len(re.findall(r"\bfor\b|\bwhile\b", code_to_measure))
            if for_count == 1:
                max_loop_nesting = 1
            elif for_count > 1 and re.search(r"for[^{};]+for", code_to_measure):
                max_loop_nesting = 2

        return max_loop_nesting

    def _derive_time_complexity(
        self,
        loop_depth: int,
        has_sort: bool,
        has_binary_search: bool,
        is_recursive: bool,
        rec_type: str,
    ) -> str:
        if is_recursive:
            if rec_type == "divide_and_conquer":
                return "O(log n)"
            return "O(n)"

        if loop_depth == 0:
            if has_binary_search:
                return "O(log n)"
            if has_sort:
                return "O(n log n)"
            return "O(1)"

        if loop_depth == 1:
            if has_binary_search:
                return "O(n log n)"
            if has_sort:
                return "O(n² log n)"
            return "O(n)"

        if loop_depth == 2:
            return "O(n²)"

        if loop_depth == 3:
            return "O(n³)"

        if loop_depth > 3:
            return f"O(n^{loop_depth})"

        return "Unable to determine"

    def _derive_space_complexity(self, code_clean: str, is_recursive: bool, rec_type: str) -> str:
        # Check C++ and Java collections and dynamic arrays
        patterns = [
            r"\bvector\s*<",
            r"\bunordered_map\s*<",
            r"\bmap\s*<",
            r"\bunordered_set\s*<",
            r"\bset\s*<",
            r"\bqueue\s*<",
            r"\bstack\s*<",
            r"\bpriority_queue\s*<",
            r"\bnew\s+\w+\s*\[",
            r"\bnew\s+ArrayList\b",
            r"\bnew\s+HashMap\b",
            r"\bnew\s+HashSet\b",
            r"\bnew\s+LinkedList\b",
            r"\bnew\s+ArrayDeque\b",
            r"\bMap\s*<",
            r"\bSet\s*<",
            r"\bList\s*<",
        ]
        has_collection = any(re.search(p, code_clean) for p in patterns)

        if has_collection:
            return "O(n)"

        if is_recursive:
            if rec_type == "divide_and_conquer":
                return "O(log n)"
            return "O(n)"

        return "O(1)"


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

def analyze_complexity(language: str, solution_code: str) -> Dict[str, str]:
    """
    Analyze the given solution code and return a dictionary containing:
    {
        "time_complexity": "...",
        "space_complexity": "..."
    }
    """
    if not solution_code or not solution_code.strip():
        return {
            "time_complexity": "Unable to determine",
            "space_complexity": "Unable to determine",
        }

    norm_lang = (language or "").strip().lower()

    try:
        if norm_lang in ("python", "py"):
            analyzer = PythonComplexityAnalyzer()
            return analyzer.analyze(solution_code).to_dict()

        if norm_lang in ("c++", "cpp", "java"):
            analyzer = CompiledLanguageComplexityAnalyzer(language)
            return analyzer.analyze(solution_code).to_dict()

        # Fallback for unknown language
        return {
            "time_complexity": "Unable to determine",
            "space_complexity": "Unable to determine",
        }
    except Exception:
        return {
            "time_complexity": "Unable to determine",
            "space_complexity": "Unable to determine",
        }
