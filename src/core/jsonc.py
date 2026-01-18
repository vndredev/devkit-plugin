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
        Content without comments (still may have trailing commas).
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


def strip_trailing_commas(content: str) -> str:
    """Remove trailing commas from JSON content.

    Handles:
    - ,] → ]
    - ,} → }

    Preserves strings containing comma sequences.

    Args:
        content: JSON content (comments already stripped).

    Returns:
        Valid JSON content without trailing commas.
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

        # Handle trailing commas only outside strings
        if not in_string and char == ",":
            # Look ahead for ] or } (skipping whitespace)
            j = i + 1
            while j < len(content) and content[j] in " \t\n\r":
                j += 1

            if j < len(content) and content[j] in "]}":
                # Skip this trailing comma
                i += 1
                continue

        result.append(char)
        i += 1

    return "".join(result)


def parse_jsonc(content: str) -> str:
    """Convert JSONC to valid JSON.

    Removes comments and trailing commas to produce valid JSON
    that can be parsed with json.loads().

    Args:
        content: JSONC content with comments and/or trailing commas.

    Returns:
        Valid JSON string.
    """
    # First strip comments, then trailing commas
    no_comments = strip_comments(content)
    return strip_trailing_commas(no_comments)
