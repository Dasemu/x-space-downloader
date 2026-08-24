# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable)
pip install -e .

# Run the CLI
x-space-dl <URL>
python -m src.main <URL>

# Run all tests
pytest

# Run a single test
pytest tests/test_validator.py::test_valid_x_url

# Run only unit tests (skip integration)
pytest -m "not integration"

# Run only integration tests
pytest -m integration
```

## Architecture

Three-module CLI tool that wraps yt-dlp to download X/Twitter Space recordings as MP3:

- **`src/main.py`** — Click CLI entry point (`cli`). Validates URL via validator, then delegates to downloader. Registered as `x-space-dl` console script.
- **`src/validator.py`** — `validate_space_url()` returns `(is_valid, space_id, error_message)` tuple. Accepts both `x.com` and `twitter.com` domains.
- **`src/downloader.py`** — `download_space()` configures yt-dlp with `bestaudio/best` format and FFmpeg MP3 postprocessor. Output files are named `space_{SPACE_ID}.mp3`. Raises `DownloadError` on failure.

Tests mock `yt_dlp.YoutubeDL` — no network calls in unit tests. Integration tests use the `@pytest.mark.integration` marker.

## Dependencies

Runtime: `yt-dlp`, `click`. System: `ffmpeg`. Dev: `pytest`, `pytest-mock`.
