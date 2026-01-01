# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Utilities for computing text differences at character level."""

from typing import List, Dict, Optional
import diff_match_patch as dmp_module


def compute_character_diff(old_text: Optional[str], new_text: Optional[str]) -> List[Dict[str, str]]:
    """Compute character-level differences between two text strings.

    Uses the diff-match-patch algorithm to compute precise character-level
    differences between old and new text versions. Returns a list of operations
    that transform old_text into new_text.

    Args:
        old_text: The original text (can be None or empty string).
        new_text: The modified text (can be None or empty string).

    Returns:
        A list of dictionaries representing diff operations. Each dictionary has:
        - "op": Operation type ("equal", "delete", or "insert")
        - "text": The text content for this operation

        Example:
            compute_character_diff("Hello world", "Hello world.")
            Returns:
            [
                {"op": "equal", "text": "Hello world"},
                {"op": "insert", "text": "."}
            ]

    Note:
        - None values are treated as empty strings
        - Empty strings are handled gracefully
        - The algorithm optimizes for human readability of diffs
    """
    # Handle None cases by converting to empty strings
    old_text = old_text or ""
    new_text = new_text or ""

    # Create diff_match_patch instance
    dmp = dmp_module.diff_match_patch()

    # Compute the diff
    diffs = dmp.diff_main(old_text, new_text)

    # Optimize for human readability (cleanup semantic diffs)
    dmp.diff_cleanupSemantic(diffs)

    # Convert to our expected format
    result = []
    for operation, text in diffs:
        if operation == dmp_module.diff_match_patch.DIFF_EQUAL:
            op_type = "equal"
        elif operation == dmp_module.diff_match_patch.DIFF_DELETE:
            op_type = "delete"
        elif operation == dmp_module.diff_match_patch.DIFF_INSERT:
            op_type = "insert"
        else:
            # This should never happen, but handle defensively
            continue

        result.append({"op": op_type, "text": text})

    return result
