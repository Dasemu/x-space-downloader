# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable)
pip install -e .

# Run the CLI (video mode by default)
x-space-dl <URL>
x-space-dl --mode audio <URL>
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

CLI tool that downloads X/Twitter Space recordings and renders them as an MP4 replay with a participant view, or as plain MP3 audio:

- **`src/main.py`** — Click CLI entry point (`cli`). Validates the URL, then delegates to `download_space` (audio mode) or `download_space_video` (video mode, default). Registered as `x-space-dl` console script.
- **`src/validator.py`** — `validate_space_url()` returns `(is_valid, space_id, error_message)`. Accepts both `x.com` and `twitter.com` domains.
- **`src/downloader.py`** — `download_space()` wraps yt-dlp for audio extraction. `download_space_video()` fetches metadata/timeline through `XApiClient`, downloads the audio, and renders the MP4 via `video.render_space_video()`.
- **`src/x_api.py`** — `XApiClient` calls X's web GraphQL (`AudioSpaceById`) and the Periscope replay chat endpoints to build participant metadata and a speaker timeline. Requires the `X_BEARER_TOKEN` environment variable (see README).
- **`src/video.py`** — Renders MP4 frames (Pillow) of the participant view and pipes them into ffmpeg alongside the audio track.
- **`src/models.py`** — Shared dataclasses: `Participant`, `SpaceMetadata`, `SpeakerInterval`.

Tests mock `yt_dlp.YoutubeDL` and outbound HTTP calls — no real network access in unit tests. Integration tests use the `@pytest.mark.integration` marker.

## Dependencies

Runtime: `yt-dlp`, `click`, `requests`, `Pillow`. System: `ffmpeg`. Dev: `pytest`, `pytest-mock`.
