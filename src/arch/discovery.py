"""Code discovery - finds similar/duplicate code patterns.

TIER 2: May import from core, lib.

Scans codebase to find existing functions, classes, and patterns
to prevent duplication when writing new code.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from lib.config import get, get_project_root


@dataclass
class CodeMatch:
    """A matching code element found in the codebase."""

    name: str
    type: str  # "function", "class", "method"
    file: str
    line: int
    signature: str
    similarity: float  # 0.0 - 1.0


def extract_definitions_from_content(content: str) -> list[dict]:
    """Extract function and class definitions from Python source.

    Args:
        content: Python source code.

    Returns:
        List of dicts with name, type, line, signature.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    definitions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Get function signature
            args = []
            for arg in node.args.args:
                arg_str = arg.arg
                if arg.annotation:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                args.append(arg_str)

            signature = f"def {node.name}({', '.join(args)})"
            if node.returns:
                signature += f" -> {ast.unparse(node.returns)}"

            definitions.append(
                {
                    "name": node.name,
                    "type": "function",
                    "line": node.lineno,
                    "signature": signature,
                }
            )

        elif isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]
            signature = f"class {node.name}"
            if bases:
                signature += f"({', '.join(bases)})"

            definitions.append(
                {
                    "name": node.name,
                    "type": "class",
                    "line": node.lineno,
                    "signature": signature,
                }
            )

    return definitions


def extract_definitions_from_file(file_path: Path) -> list[dict]:
    """Extract definitions from a Python file.

    Args:
        file_path: Path to Python file.

    Returns:
        List of definition dicts with file path added.
    """
    try:
        content = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        return []

    definitions = extract_definitions_from_content(content)
    for d in definitions:
        d["file"] = str(file_path)

    return definitions


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two names.

    Uses multiple strategies:
    1. Exact match (1.0)
    2. Case-insensitive match (0.95)
    3. One contains the other (0.8)
    4. Common words overlap (0.3-0.7)

    Args:
        name1: First name.
        name2: Second name.

    Returns:
        Similarity score 0.0 - 1.0.
    """
    # Exact match
    if name1 == name2:
        return 1.0

    # Case-insensitive match
    if name1.lower() == name2.lower():
        return 0.95

    n1_lower = name1.lower()
    n2_lower = name2.lower()

    # One contains the other
    if n1_lower in n2_lower or n2_lower in n1_lower:
        return 0.8

    # Split into words (camelCase and snake_case)
    def split_name(name: str) -> set[str]:
        # Split on underscores and camelCase
        words = re.split(r"_|(?=[A-Z])", name)
        return {w.lower() for w in words if w}

    words1 = split_name(name1)
    words2 = split_name(name2)

    if not words1 or not words2:
        return 0.0

    # Calculate Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)

    if union == 0:
        return 0.0

    return intersection / union * 0.7  # Max 0.7 for word overlap


def scan_codebase(
    root: Path | None = None, include_patterns: list[str] | None = None
) -> list[dict]:
    """Scan codebase for all function and class definitions.

    Args:
        root: Project root directory.
        include_patterns: Glob patterns for files to include (default: src/**/*.py).

    Returns:
        List of all definitions found.
    """
    if root is None:
        root = get_project_root()

    if include_patterns is None:
        # Default: scan src/ directory
        include_patterns = ["src/**/*.py"]

    all_definitions = []

    for pattern in include_patterns:
        for file_path in root.glob(pattern):
            if file_path.is_file():
                definitions = extract_definitions_from_file(file_path)
                all_definitions.extend(definitions)

    return all_definitions


def find_similar_code(
    new_content: str,
    threshold: float = 0.7,
    root: Path | None = None,
    exclude_file: str | None = None,
) -> list[CodeMatch]:
    """Find similar code in codebase for new content.

    Args:
        new_content: New Python code to check.
        threshold: Minimum similarity score (0.0 - 1.0).
        root: Project root directory.
        exclude_file: File path to exclude from search (the file being edited).

    Returns:
        List of CodeMatch objects for similar code found.
    """
    # Extract definitions from new code
    new_definitions = extract_definitions_from_content(new_content)
    if not new_definitions:
        return []

    # Get scan patterns from config
    patterns = get("discovery.scan_patterns", ["src/**/*.py"])

    # Scan existing codebase
    existing_definitions = scan_codebase(root, patterns)

    # Filter out definitions from the file being edited
    if exclude_file:
        existing_definitions = [d for d in existing_definitions if d["file"] != exclude_file]

    # Find matches
    matches = []

    for new_def in new_definitions:
        for existing_def in existing_definitions:
            # Skip if same type doesn't match
            if new_def["type"] != existing_def["type"]:
                continue

            similarity = calculate_name_similarity(new_def["name"], existing_def["name"])

            if similarity >= threshold:
                matches.append(
                    CodeMatch(
                        name=existing_def["name"],
                        type=existing_def["type"],
                        file=existing_def["file"],
                        line=existing_def["line"],
                        signature=existing_def["signature"],
                        similarity=similarity,
                    )
                )

    # Sort by similarity (highest first)
    matches.sort(key=lambda m: m.similarity, reverse=True)

    return matches


def find_duplicates_for_name(
    name: str,
    code_type: str = "function",
    threshold: float = 0.7,
    root: Path | None = None,
) -> list[CodeMatch]:
    """Find similar definitions for a given name.

    Args:
        name: Function or class name to search for.
        code_type: Type to search for ("function", "class", or "any").
        threshold: Minimum similarity score.
        root: Project root directory.

    Returns:
        List of CodeMatch objects.
    """
    patterns = get("discovery.scan_patterns", ["src/**/*.py"])
    existing_definitions = scan_codebase(root, patterns)

    matches = []

    for existing_def in existing_definitions:
        if code_type != "any" and existing_def["type"] != code_type:
            continue

        similarity = calculate_name_similarity(name, existing_def["name"])

        if similarity >= threshold:
            matches.append(
                CodeMatch(
                    name=existing_def["name"],
                    type=existing_def["type"],
                    file=existing_def["file"],
                    line=existing_def["line"],
                    signature=existing_def["signature"],
                    similarity=similarity,
                )
            )

    matches.sort(key=lambda m: m.similarity, reverse=True)
    return matches


def format_matches_report(matches: list[CodeMatch], context: str = "") -> str:
    """Format matches as a readable report.

    Args:
        matches: List of code matches.
        context: Optional context (e.g., "for function 'extract_imports'").

    Returns:
        Formatted report string.
    """
    if not matches:
        return "No similar code found."

    lines = []
    if context:
        lines.append(f"Similar code found {context}:")
    else:
        lines.append("Similar code found:")
    lines.append("")

    for match in matches[:5]:  # Limit to top 5
        similarity_pct = int(match.similarity * 100)
        lines.append(f"  [{similarity_pct}%] {match.file}:{match.line}")
        lines.append(f"       {match.signature}")
        lines.append("")

    if len(matches) > 5:
        lines.append(f"  ... and {len(matches) - 5} more matches")

    return "\n".join(lines)
