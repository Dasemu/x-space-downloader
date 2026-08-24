# X Space Downloader

Three-module CLI tool that wraps yt-dlp to download X/Twitter Space recordings as MP3.

## Commands

```bash
pip install -e .                          # Install (editable)
x-space-dl <URL>                          # Run the CLI
python -m src.main <URL>                  # Alternative invocation
pytest                                    # Run all tests
pytest -m "not integration"               # Unit tests only
pytest -m integration                     # Integration tests only
pytest tests/test_validator.py::test_valid_x_url  # Single test
```

## Architecture

- **`src/main.py`** -- Click CLI entry point. Validates URL via validator, delegates to downloader. Registered as `x-space-dl` console script.
- **`src/validator.py`** -- `validate_space_url()` returns `(is_valid, space_id, error_message)`. Accepts both `x.com` and `twitter.com` domains.
- **`src/downloader.py`** -- `download_space()` configures yt-dlp with `bestaudio/best` format and FFmpeg MP3 postprocessor. Output: `space_{SPACE_ID}.mp3`. Raises `DownloadError` on failure.

## Dependencies

Runtime: `yt-dlp`, `click`. System: `ffmpeg`. Dev: `pytest`, `pytest-mock`.

Tests mock `yt_dlp.YoutubeDL` -- no network calls in unit tests. Integration tests use `@pytest.mark.integration`.
