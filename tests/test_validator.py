import pytest
from src.validator import validate_space_url


def test_validate_space_url_valid():
    """Test that valid X Space URL is accepted."""
    url = "https://x.com/i/spaces/1ZkKzZWnVRRKv"
    is_valid, space_id, error = validate_space_url(url)

    assert is_valid is True
    assert space_id == "1ZkKzZWnVRRKv"
    assert error is None


def test_validate_space_url_invalid_format():
    """Test that invalid URLs are rejected."""
    invalid_urls = [
        "https://x.com/spaces/1ZkKzZWnVRRKv",  # Missing /i/
        "https://x.com/i/spaces/",  # Missing space ID
        "not a url",  # Completely invalid
        "",  # Empty string
    ]

    for url in invalid_urls:
        is_valid, space_id, error = validate_space_url(url)
        assert is_valid is False
        assert space_id is None
        assert "Invalid URL format" in error


def test_validate_space_url_twitter_domain():
    """Test that twitter.com URLs are also accepted."""
    url = "https://twitter.com/i/spaces/1ZkKzZWnVRRKv"
    is_valid, space_id, error = validate_space_url(url)

    assert is_valid is True
    assert space_id == "1ZkKzZWnVRRKv"
    assert error is None
