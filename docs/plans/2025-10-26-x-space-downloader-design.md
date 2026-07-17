# X Space Downloader - Design Document

**Date:** 2025-10-26
**Status:** Approved

## Overview

A Python CLI tool that downloads X (Twitter) Space recordings and outputs them as MP3 files. Takes a Space URL as input and produces an audio file.

## Requirements

- **Input:** X Space recording URL (e.g., `https://x.com/i/spaces/1ZkKzZWnVRRKv`)
- **Output:** MP3 audio file
- **Interface:** Command-line tool
- **Authentication:** Supports X account credentials via cookies
- **Scope:** Recordings only (not live Spaces)
- **Error Handling:** Clear error messages for invalid or non-recording URLs

## Architecture Overview

### Technology Choices

- **Language:** Python
- **Core Engine:** yt-dlp (handles X authentication and media extraction)
- **CLI Framework:** Click (argument parsing and user interface)
- **Pattern:** Thin wrapper around yt-dlp

### Project Structure

```
x-space-downloader/
├── src/
│   ├── __init__.py
│   ├── main.py          # CLI entry point with argument parsing
│   ├── downloader.py    # Wraps yt-dlp functionality
│   └── validator.py     # URL validation and error handling
├── tests/
│   ├── test_validator.py
│   └── test_downloader.py
├── requirements.txt     # Dependencies: yt-dlp, click
├── setup.py            # Makes it installable
└── README.md
```

### User Workflow

```bash
x-space-dl --cookies cookies.txt https://x.com/i/spaces/1ZkKzZWnVRRKv
# Output: space_1ZkKzZWnVRRKv.mp3
```

## Component Design

### validator.py

**Responsibilities:**
- Validate URL format (must match X Spaces pattern: `https://x.com/i/spaces/{SPACE_ID}`)
- Check if URL points to a recording vs live Space
- Return clear error messages for invalid inputs

**Key Interface:**
```python
def validate_space_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates X Space URL.

    Returns:
        (is_valid, space_id, error_message)
    """
```

### downloader.py

**Responsibilities:**
- Configure yt-dlp options (format: mp3, quality, output template)
- Pass cookie file to yt-dlp for authentication
- Translate yt-dlp output/errors to user-friendly messages
- Show download progress

**Key Interface:**
```python
def download_space(
    space_url: str,
    output_dir: str,
    cookies_file: Optional[str]
) -> str:
    """
    Downloads Space recording using yt-dlp.

    Returns:
        Path to downloaded MP3 file
    """
```

**yt-dlp Configuration:**
- Output format: mp3 (audio only)
- Output template: `space_{space_id}.mp3`
- Post-processing: convert to mp3 if needed
- Progress hooks for user feedback

### main.py

**Responsibilities:**
- CLI argument parsing with Click
- Orchestrate validation → download flow
- Handle and display errors appropriately
- Exit with appropriate status codes

**CLI Arguments:**
- `URL` (required): X Space URL
- `--cookies` (optional): Path to cookies file
- `--output` (optional): Output directory (default: current directory)

**Exit Codes:**
- `0`: Success
- `1`: Invalid URL
- `2`: Download failed
- `3`: Authentication required

## Data Flow

1. User provides URL + optional cookies file
2. **Validator** checks URL format → extracts space_id
3. **Downloader** configures yt-dlp with:
   - Output format: mp3 (audio only)
   - Output template: `space_{space_id}.mp3`
   - Cookies file if provided
   - Post-processing: convert to mp3 if needed
4. yt-dlp fetches metadata, downloads audio stream, converts to mp3
5. Return file path to user

## Error Handling

| Error Scenario | Detection | User Message |
|----------------|-----------|--------------|
| Invalid URL format | Validator regex check | "Invalid URL format. Expected: https://x.com/i/spaces/{SPACE_ID}" |
| Space doesn't exist | yt-dlp 404 error | "Recording not found. Check URL or Space may be deleted." |
| Authentication required | yt-dlp auth error | "Authentication required. Please provide cookies file with --cookies" |
| Network errors | yt-dlp timeout/connection | "Network error. Check connection and try again." |
| Space is live | Validator metadata check | "Error: This is a live Space, not a recording." |
| Disk space/permissions | File system errors | "Cannot write to output directory. Check permissions and disk space." |

## Authentication

**Cookie-based Authentication:**
- User exports cookies from logged-in X session
- Provides cookie file path via `--cookies` flag
- yt-dlp uses cookies for authenticated requests

**Cookie Export Instructions:**
- Browser extensions: "Get cookies.txt", "cookies.txt"
- Manual: Export via browser DevTools
- Instructions included in README

## Testing Strategy

**Unit Tests:**
- Validator: Test various URL formats, valid/invalid patterns
- Error message generation

**Integration Tests:**
- Full download flow with yt-dlp
- Use test Space URLs or mock yt-dlp calls
- Cookie authentication flow

**Error Scenario Tests:**
- Invalid URLs
- Missing cookies
- Network failures
- Live Space detection

## Dependencies

**Core:**
- `yt-dlp`: Media downloading and extraction
- `click`: CLI framework

**Development:**
- `pytest`: Testing framework
- `pytest-mock`: Mocking for tests

## Future Considerations (Out of Scope)

- Live Space recording
- Batch downloading multiple Spaces
- GUI interface
- Format options beyond MP3
- Metadata extraction (speakers, title, description)
