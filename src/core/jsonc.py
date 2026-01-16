"""JSONC parser - JSON with Comments support.

TIER 0: No internal imports, only Python stdlib.
"""


def strip_comments(content: str) -> str:
    """Strip JSONC comments from content.

    Removes:
    - Single-line comments: // comment
    - Multi-line comments: /* comment */

    Preserves strings containing // or /* sequences.

    Args:
        content: JSONC content with comments.

    Returns:
        Valid JSON content without comments.
    """
    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(content):
        char = content[i]

        # Handle escape sequences in strings
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        # Track string boundaries
        if char == '"' and not escape_next:
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        # Handle escape character
        if char == "\\" and in_string:
            escape_next = True
            result.append(char)
            i += 1
            continue

        # Skip comments only outside strings
        if not in_string:
            # Single-line comment
            if content[i : i + 2] == "//":
                # Skip until end of line
                while i < len(content) and content[i] != "\n":
                    i += 1
                continue

            # Multi-line comment
            if content[i : i + 2] == "/*":
                # Skip until */
                i += 2
                while i < len(content) - 1:
                    if content[i : i + 2] == "*/":
                        i += 2
                        break
                    i += 1
                continue

        result.append(char)
        i += 1

    return "".join(result)
