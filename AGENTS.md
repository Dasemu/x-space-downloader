# X Space Downloader

CLI tool that downloads X/Twitter Space recordings and renders them as an MP4 replay (participant view + audio) by default, or as plain MP3 audio.

## Commands

```bash
pip install -e .                          # Install (editable)
x-space-dl <URL>                          # Run the CLI (video mode by default)
x-space-dl --mode audio <URL>             # Audio-only MP3 mode
python -m src.main <URL>                  # Alternative invocation
pytest                                     # Run all tests
pytest -m "not integration"                # Unit tests only
pytest -m integration                      # Integration tests only
pytest tests/test_validator.py::test_valid_x_url  # Single test
```

## Architecture

- **`src/main.py`** -- Click CLI entry point. Validates URL via validator, then delegates to `download_space` (audio) or `download_space_video` (video, default). Registered as `x-space-dl` console script.
- **`src/validator.py`** -- `validate_space_url()` returns `(is_valid, space_id, error_message)`. Accepts both `x.com` and `twitter.com` domains.
- **`src/downloader.py`** -- `download_space()` wraps yt-dlp for audio extraction. `download_space_video()` fetches Space metadata/timeline via `XApiClient`, downloads audio, then renders the MP4 via `video.render_space_video()`.
- **`src/x_api.py`** -- `XApiClient` calls X's web GraphQL (`AudioSpaceById`) and Periscope replay chat endpoints to fetch title, host, participants, and a speaker timeline. Requires the `X_BEARER_TOKEN` environment variable.
- **`src/video.py`** -- Renders the MP4 participant-view frames (Pillow) and pipes them through ffmpeg alongside the audio track.
- **`src/models.py`** -- Shared dataclasses: `Participant`, `SpaceMetadata`, `SpeakerInterval`.

## Dependencies

Runtime: `yt-dlp`, `click`, `requests`, `Pillow`. System: `ffmpeg`. Dev: `pytest`, `pytest-mock`.

Tests mock `yt_dlp.YoutubeDL` and network calls -- no real network access in unit tests. Integration tests use `@pytest.mark.integration`.
