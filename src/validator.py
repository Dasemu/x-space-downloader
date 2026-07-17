import re
from typing import Tuple, Optional


def validate_space_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates X Space URL format.

    Args:
        url: The URL to validate

    Returns:
        Tuple of (is_valid, space_id, error_message)
    """
    # Pattern for X Space URLs (supports both x.com and twitter.com)
    pattern = r"https://(x|twitter)\.com/i/spaces/([a-zA-Z0-9]+)"
    match = re.match(pattern, url)

    if not match:
        return False, None, "Invalid URL format. Expected: https://x.com/i/spaces/{SPACE_ID}"

    space_id = match.group(2)  # Changed from group(1) to group(2)
    return True, space_id, None
