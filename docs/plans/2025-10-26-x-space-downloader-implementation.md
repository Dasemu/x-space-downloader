# X Space Downloader Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI tool that downloads X (Twitter) Space recordings and outputs MP3 files.

**Architecture:** Thin wrapper around yt-dlp with URL validation, error handling, and Click-based CLI. Cookie-based authentication for X access.

**Tech Stack:** Python, yt-dlp, Click, pytest

---

## Task 1: Project Setup and Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `setup.py`
- Create: `src/__init__.py`
- Create: `.gitignore`

**Step 1: Create requirements.txt**

Create the file with dependencies:

```txt
yt-dlp>=2024.0.0
click>=8.0.0
```

**Step 2: Create setup.py**

Create the file to make the package installable:

```python
from setuptools import setup, find_packages

setup(
    name="x-space-downloader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "yt-dlp>=2024.0.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "x-space-dl=src.main:cli",
        ],
    },
    python_requires=">=3.8",
)
```

**Step 3: Create src package init file**

```bash
mkdir -p src
touch src/__init__.py
```

**Step 4: Create .gitignore**

```txt
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/
dist/
build/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Downloads
*.mp3
*.m4a
cookies.txt
```

**Step 5: Install in development mode**

Run: `pip install -e .`
Expected: Package installed successfully

**Step 6: Commit**

```bash
git add requirements.txt setup.py src/__init__.py .gitignore
git commit -m "feat: add project setup and dependencies"
```

---

## Task 2: URL Validator (TDD)

**Files:**
- Create: `tests/test_validator.py`
- Create: `src/validator.py`

**Step 1: Create test directory**

```bash
mkdir -p tests
touch tests/__init__.py
```

**Step 2: Write failing test for valid URL**

Create `tests/test_validator.py`:

```python
import pytest
from src.validator import validate_space_url


def test_validate_space_url_valid():
    """Test that valid X Space URL is accepted."""
    url = "https://x.com/i/spaces/1ZkKzZWnVRRKv"
    is_valid, space_id, error = validate_space_url(url)

    assert is_valid is True
    assert space_id == "1ZkKzZWnVRRKv"
    assert error is None
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_validator.py::test_validate_space_url_valid -v`
Expected: FAIL with "cannot import name 'validate_space_url'"

**Step 4: Write minimal validator implementation**

Create `src/validator.py`:

```python
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
    # Pattern for X Space URLs
    pattern = r"https://x\.com/i/spaces/([a-zA-Z0-9]+)"
    match = re.match(pattern, url)

    if not match:
        return False, None, "Invalid URL format. Expected: https://x.com/i/spaces/{SPACE_ID}"

    space_id = match.group(1)
    return True, space_id, None
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_validator.py::test_validate_space_url_valid -v`
Expected: PASS

**Step 6: Commit**

```bash
git add tests/__init__.py tests/test_validator.py src/validator.py
git commit -m "feat: add URL validator for X Space URLs"
```

---

## Task 3: Validator Error Cases (TDD)

**Files:**
- Modify: `tests/test_validator.py`

**Step 1: Write test for invalid URL formats**

Add to `tests/test_validator.py`:

```python
def test_validate_space_url_invalid_format():
    """Test that invalid URLs are rejected."""
    invalid_urls = [
        "https://twitter.com/i/spaces/1ZkKzZWnVRRKv",  # Old twitter.com
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
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_validator.py::test_validate_space_url_invalid_format -v`
Expected: PASS (implementation already handles these)

**Step 3: Write test for twitter.com URL support**

Add to `tests/test_validator.py`:

```python
def test_validate_space_url_twitter_domain():
    """Test that twitter.com URLs are also accepted."""
    url = "https://twitter.com/i/spaces/1ZkKzZWnVRRKv"
    is_valid, space_id, error = validate_space_url(url)

    assert is_valid is True
    assert space_id == "1ZkKzZWnVRRKv"
    assert error is None
```

**Step 4: Run test to verify it fails**

Run: `pytest tests/test_validator.py::test_validate_space_url_twitter_domain -v`
Expected: FAIL

**Step 5: Update validator to support twitter.com**

Modify `src/validator.py`:

```python
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
```

**Step 6: Run all validator tests**

Run: `pytest tests/test_validator.py -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add tests/test_validator.py src/validator.py
git commit -m "feat: add validator error cases and twitter.com support"
```

---

## Task 4: Downloader Module (TDD)

**Files:**
- Create: `tests/test_downloader.py`
- Create: `src/downloader.py`

**Step 1: Write failing test for downloader**

Create `tests/test_downloader.py`:

```python
import pytest
from unittest.mock import Mock, patch
from src.downloader import download_space


def test_download_space_basic(tmp_path):
    """Test basic download functionality."""
    space_url = "https://x.com/i/spaces/1ZkKzZWnVRRKv"

    with patch('src.downloader.yt_dlp.YoutubeDL') as mock_ytdl_class:
        # Mock the YoutubeDL instance
        mock_ytdl = Mock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        mock_ytdl.extract_info.return_value = {'id': '1ZkKzZWnVRRKv'}

        # Call download_space
        result = download_space(
            space_url=space_url,
            output_dir=str(tmp_path),
            cookies_file=None
        )

        # Verify YoutubeDL was called
        mock_ytdl.extract_info.assert_called_once_with(space_url, download=True)

        # Verify result contains expected filename
        assert "space_1ZkKzZWnVRRKv" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_downloader.py::test_download_space_basic -v`
Expected: FAIL with "cannot import name 'download_space'"

**Step 3: Write minimal downloader implementation**

Create `src/downloader.py`:

```python
import os
import yt_dlp
from typing import Optional


def download_space(
    space_url: str,
    output_dir: str,
    cookies_file: Optional[str] = None
) -> str:
    """
    Downloads X Space recording using yt-dlp.

    Args:
        space_url: URL of the X Space recording
        output_dir: Directory to save the MP3 file
        cookies_file: Optional path to cookies file for authentication

    Returns:
        Path to the downloaded MP3 file
    """
    # Extract space ID from URL for filename
    space_id = space_url.split('/')[-1]

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f'space_{space_id}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': False,
        'no_warnings': False,
    }

    # Add cookies if provided
    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    # Download with yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(space_url, download=True)

    # Return the expected output path
    return os.path.join(output_dir, f'space_{space_id}.mp3')
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_downloader.py::test_download_space_basic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_downloader.py src/downloader.py
git commit -m "feat: add downloader module with yt-dlp integration"
```

---

## Task 5: Downloader Error Handling (TDD)

**Files:**
- Modify: `tests/test_downloader.py`
- Modify: `src/downloader.py`

**Step 1: Write test for download errors**

Add to `tests/test_downloader.py`:

```python
from src.downloader import DownloadError


def test_download_space_error_handling(tmp_path):
    """Test that download errors are properly caught and wrapped."""
    space_url = "https://x.com/i/spaces/invalid"

    with patch('src.downloader.yt_dlp.YoutubeDL') as mock_ytdl_class:
        mock_ytdl = Mock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        mock_ytdl.extract_info.side_effect = Exception("Video unavailable")

        with pytest.raises(DownloadError) as exc_info:
            download_space(
                space_url=space_url,
                output_dir=str(tmp_path),
                cookies_file=None
            )

        assert "Failed to download" in str(exc_info.value)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_downloader.py::test_download_space_error_handling -v`
Expected: FAIL with "cannot import name 'DownloadError'"

**Step 3: Add error handling to downloader**

Modify `src/downloader.py`:

```python
import os
import yt_dlp
from typing import Optional


class DownloadError(Exception):
    """Raised when download fails."""
    pass


def download_space(
    space_url: str,
    output_dir: str,
    cookies_file: Optional[str] = None
) -> str:
    """
    Downloads X Space recording using yt-dlp.

    Args:
        space_url: URL of the X Space recording
        output_dir: Directory to save the MP3 file
        cookies_file: Optional path to cookies file for authentication

    Returns:
        Path to the downloaded MP3 file

    Raises:
        DownloadError: If download fails
    """
    # Extract space ID from URL for filename
    space_id = space_url.split('/')[-1]

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f'space_{space_id}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': False,
        'no_warnings': False,
    }

    # Add cookies if provided
    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    # Download with yt-dlp
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(space_url, download=True)
    except Exception as e:
        raise DownloadError(f"Failed to download Space: {str(e)}")

    # Return the expected output path
    return os.path.join(output_dir, f'space_{space_id}.mp3')
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_downloader.py::test_download_space_error_handling -v`
Expected: PASS

**Step 5: Run all downloader tests**

Run: `pytest tests/test_downloader.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add tests/test_downloader.py src/downloader.py
git commit -m "feat: add error handling to downloader"
```

---

## Task 6: CLI Main Module (TDD)

**Files:**
- Create: `tests/test_main.py`
- Create: `src/main.py`

**Step 1: Write test for CLI entry point**

Create `tests/test_main.py`:

```python
import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock
from src.main import cli


def test_cli_valid_url(tmp_path):
    """Test CLI with valid URL."""
    runner = CliRunner()

    with patch('src.main.validate_space_url') as mock_validate, \
         patch('src.main.download_space') as mock_download:

        mock_validate.return_value = (True, "1ZkKzZWnVRRKv", None)
        mock_download.return_value = str(tmp_path / "space_1ZkKzZWnVRRKv.mp3")

        result = runner.invoke(cli, ['https://x.com/i/spaces/1ZkKzZWnVRRKv'])

        assert result.exit_code == 0
        assert "Successfully downloaded" in result.output
        assert "space_1ZkKzZWnVRRKv.mp3" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py::test_cli_valid_url -v`
Expected: FAIL with "cannot import name 'cli'"

**Step 3: Write minimal CLI implementation**

Create `src/main.py`:

```python
import click
import os
from src.validator import validate_space_url
from src.downloader import download_space, DownloadError


@click.command()
@click.argument('url')
@click.option('--cookies', '-c', type=click.Path(exists=True), help='Path to cookies file')
@click.option('--output', '-o', type=click.Path(), default='.', help='Output directory')
def cli(url, cookies, output):
    """
    Download X (Twitter) Space recordings as MP3 files.

    Example:
        x-space-dl https://x.com/i/spaces/1ZkKzZWnVRRKv
    """
    # Validate URL
    is_valid, space_id, error = validate_space_url(url)
    if not is_valid:
        click.echo(f"Error: {error}", err=True)
        raise click.Exit(1)

    # Download the Space
    try:
        click.echo(f"Downloading Space: {space_id}")
        output_path = download_space(url, output, cookies)
        click.echo(f"Successfully downloaded to: {output_path}")
    except DownloadError as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Exit(2)


if __name__ == '__main__':
    cli()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py::test_cli_valid_url -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_main.py src/main.py
git commit -m "feat: add CLI main module with Click integration"
```

---

## Task 7: CLI Error Cases (TDD)

**Files:**
- Modify: `tests/test_main.py`

**Step 1: Write test for invalid URL**

Add to `tests/test_main.py`:

```python
def test_cli_invalid_url():
    """Test CLI with invalid URL."""
    runner = CliRunner()

    result = runner.invoke(cli, ['https://invalid.com/spaces/123'])

    assert result.exit_code == 1
    assert "Invalid URL format" in result.output
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_main.py::test_cli_invalid_url -v`
Expected: PASS (implementation already handles this)

**Step 3: Write test for download failure**

Add to `tests/test_main.py`:

```python
def test_cli_download_failure():
    """Test CLI when download fails."""
    runner = CliRunner()

    with patch('src.main.validate_space_url') as mock_validate, \
         patch('src.main.download_space') as mock_download:

        mock_validate.return_value = (True, "1ZkKzZWnVRRKv", None)
        mock_download.side_effect = DownloadError("Video unavailable")

        result = runner.invoke(cli, ['https://x.com/i/spaces/1ZkKzZWnVRRKv'])

        assert result.exit_code == 2
        assert "Video unavailable" in result.output
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py::test_cli_download_failure -v`
Expected: PASS (implementation already handles this)

**Step 5: Write test for cookies option**

Add to `tests/test_main.py`:

```python
def test_cli_with_cookies(tmp_path):
    """Test CLI with cookies file."""
    runner = CliRunner()

    # Create a fake cookies file
    cookies_file = tmp_path / "cookies.txt"
    cookies_file.write_text("# Netscape HTTP Cookie File\n")

    with patch('src.main.validate_space_url') as mock_validate, \
         patch('src.main.download_space') as mock_download:

        mock_validate.return_value = (True, "1ZkKzZWnVRRKv", None)
        mock_download.return_value = str(tmp_path / "space_1ZkKzZWnVRRKv.mp3")

        result = runner.invoke(cli, [
            'https://x.com/i/spaces/1ZkKzZWnVRRKv',
            '--cookies', str(cookies_file)
        ])

        assert result.exit_code == 0
        mock_download.assert_called_once()
        assert mock_download.call_args[1]['cookies_file'] == str(cookies_file)
```

**Step 6: Run all CLI tests**

Run: `pytest tests/test_main.py -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add tests/test_main.py
git commit -m "test: add CLI error cases and cookies option tests"
```

---

## Task 8: README Documentation

**Files:**
- Create: `README.md`

**Step 1: Create comprehensive README**

```markdown
# X Space Downloader

A Python CLI tool that downloads X (Twitter) Space recordings and outputs them as MP3 files.

## Features

- Download X Space recordings as MP3 files
- Support for authenticated downloads using cookies
- Simple command-line interface
- Clear error messages

## Installation

### Prerequisites

- Python 3.8 or higher
- ffmpeg (required by yt-dlp for audio conversion)

Install ffmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Install the tool

```bash
git clone https://github.com/synapz-org/x-space-downloader.git
cd x-space-downloader
pip install -e .
```

## Usage

### Basic usage

```bash
x-space-dl https://x.com/i/spaces/1ZkKzZWnVRRKv
```

This will download the Space recording and save it as `space_1ZkKzZWnVRRKv.mp3` in the current directory.

### With authentication (recommended)

For better reliability and access to private Spaces, provide cookies from your logged-in X session:

```bash
x-space-dl --cookies cookies.txt https://x.com/i/spaces/1ZkKzZWnVRRKv
```

### Specify output directory

```bash
x-space-dl --output ~/Downloads https://x.com/i/spaces/1ZkKzZWnVRRKv
```

### Full options

```bash
x-space-dl --help
```

## Exporting Cookies

To download Spaces that require authentication, you need to export cookies from your logged-in X session.

### Method 1: Browser Extension (Easiest)

1. Install a cookie export extension:
   - Chrome/Edge: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. Log in to X (twitter.com or x.com)
3. Click the extension icon and export cookies
4. Save as `cookies.txt`

### Method 2: Manual Export (Advanced)

1. Log in to X
2. Open Developer Tools (F12)
3. Go to Application/Storage → Cookies
4. Copy cookies in Netscape format to a file

## Requirements

- Python 3.8+
- yt-dlp
- click
- ffmpeg (system dependency)

## Supported URLs

The tool supports X Space URLs in these formats:

- `https://x.com/i/spaces/{SPACE_ID}`
- `https://twitter.com/i/spaces/{SPACE_ID}`

**Note:** Only recordings are supported. Live Spaces must be recorded before downloading.

## Error Messages

| Error | Meaning |
|-------|---------|
| "Invalid URL format" | URL doesn't match X Space format |
| "Failed to download Space" | Recording not found or network error |
| "Authentication required" | Space requires login (use --cookies) |

## Development

### Running tests

```bash
pip install pytest pytest-mock
pytest
```

### Project structure

```
x-space-downloader/
├── src/
│   ├── main.py          # CLI entry point
│   ├── downloader.py    # yt-dlp wrapper
│   └── validator.py     # URL validation
├── tests/
│   ├── test_main.py
│   ├── test_downloader.py
│   └── test_validator.py
└── docs/
    └── plans/           # Design documents
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Troubleshooting

### "ffmpeg not found"
Install ffmpeg using your system's package manager (see Installation section).

### "Video unavailable"
The Space recording may have been deleted or is private. Try using the --cookies option.

### "Authentication required"
Export cookies from your logged-in X session and use the --cookies option.

## Acknowledgments

Built with:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Media downloader
- [Click](https://click.palletsprojects.com/) - CLI framework
```

**Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: add comprehensive README with usage and installation"
```

---

## Task 9: Development Dependencies

**Files:**
- Create: `requirements-dev.txt`

**Step 1: Create development requirements**

```txt
pytest>=7.0.0
pytest-mock>=3.10.0
```

**Step 2: Commit**

```bash
git add requirements-dev.txt
git commit -m "chore: add development dependencies"
```

---

## Task 10: Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
import pytest
from click.testing import CliRunner
from src.main import cli


@pytest.mark.integration
def test_full_workflow_with_mocks(tmp_path):
    """Integration test for complete workflow."""
    runner = CliRunner()

    from unittest.mock import patch

    with patch('src.downloader.yt_dlp.YoutubeDL') as mock_ytdl_class:
        # Mock successful download
        mock_ytdl = mock_ytdl_class.return_value.__enter__.return_value
        mock_ytdl.extract_info.return_value = {'id': '1ZkKzZWnVRRKv'}

        # Run CLI
        result = runner.invoke(cli, [
            'https://x.com/i/spaces/1ZkKzZWnVRRKv',
            '--output', str(tmp_path)
        ])

        # Verify success
        assert result.exit_code == 0
        assert "Successfully downloaded" in result.output

        # Verify yt-dlp was called correctly
        mock_ytdl.extract_info.assert_called_once()
        call_args = mock_ytdl_class.call_args
        assert 'bestaudio' in call_args[0][0]['format']
        assert 'mp3' in call_args[0][0]['postprocessors'][0]['preferredcodec']
```

**Step 2: Run integration test**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

**Step 3: Run all tests**

Run: `pytest -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for complete workflow"
```

---

## Task 11: Push to GitHub

**Files:**
- N/A (git operations)

**Step 1: Push all commits to GitHub**

```bash
git push -u origin master
```

Expected: All commits pushed successfully

---

## Verification Steps

After completing all tasks:

1. **Install the package:**
   ```bash
   pip install -e .
   ```

2. **Run all tests:**
   ```bash
   pytest -v
   ```
   Expected: All tests pass

3. **Test CLI is installed:**
   ```bash
   x-space-dl --help
   ```
   Expected: Help text displays

4. **Test with invalid URL:**
   ```bash
   x-space-dl https://invalid.com/test
   ```
   Expected: Error message about invalid URL format

## Notes for Implementation

- **TDD strictly:** Write test first, watch it fail, implement, watch it pass
- **Commit frequently:** After each passing test
- **YAGNI:** Don't add features not in the design (no GUI, no batch downloads, etc.)
- **DRY:** Reuse validator and downloader functions, don't duplicate logic
- **Error messages:** Keep them user-friendly and actionable
- **Testing:** Mock yt-dlp in tests to avoid actual network calls
