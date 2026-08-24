# X Space Downloader

[![Tests](https://github.com/Dasemu/x-space-downloader/actions/workflows/tests.yml/badge.svg)](https://github.com/Dasemu/x-space-downloader/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Python CLI tool that downloads X (Twitter) Space recordings and renders an MP4 replay with audio and a compact participant view.

## Features

- Download X Space recordings as MP4 videos by default
- Keep the original audio-only MP3 mode
- Fetch participant metadata from X `AudioSpaceById` when cookies are provided
- Download the replay chat timeline and highlight active speakers when cookies are provided
- Accept an optional speaker timeline JSON file as a fallback/manual override
- Support for authenticated downloads using cookies
- Simple command-line interface
- Clear error messages

## Installation

### Prerequisites

- Python 3.8 or higher
- ffmpeg (required for audio conversion and MP4 rendering)

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
git clone https://github.com/Dasemu/x-space-downloader.git
cd x-space-downloader
pip install -e .
```

## Usage

### Basic usage

```bash
x-space-dl https://x.com/i/spaces/1ZkKzZWnVRRKv
```

This will download the Space recording and save it as `space_1ZkKzZWnVRRKv.mp4` in the current directory.

### Audio-only mode

```bash
x-space-dl --mode audio https://x.com/i/spaces/1ZkKzZWnVRRKv
```

This keeps the original behavior and writes `space_1ZkKzZWnVRRKv.mp3`.

### With authentication (recommended)

For better reliability and access to private Spaces, provide cookies from your logged-in X session:

```bash
x-space-dl --cookies cookies.txt https://x.com/i/spaces/1ZkKzZWnVRRKv
```

Cookies are also used to fetch the Space title, host, speakers, avatars, and replay chat timeline from X/Periscope metadata.

### Environment variables

Fetching metadata (required for the default video mode) needs a bearer token for X's web GraphQL API:

```bash
export X_BEARER_TOKEN="<token>"
```

Get this value from your own browser: open x.com while logged in, open DevTools → Network, and copy the `authorization: Bearer ...` header from any request to `x.com/i/api/graphql`. This is the public token issued to X's web client, not a personal secret, but it's not bundled with this tool — you provide your own.

`X_AUDIO_SPACE_QUERY_ID` can optionally override the GraphQL query ID used for `AudioSpaceById` if X changes it.

### Speaker timeline

With cookies, the tool automatically calls the replay `history` endpoint and builds participant/speaker timing from Space microphone events. If you already have speaker intervals from another extractor, you can override that with JSON:

```bash
x-space-dl --cookies cookies.txt --speaker-timeline speakers.json https://x.com/i/spaces/1ZkKzZWnVRRKv
```

Supported JSON shape:

```json
[
  {"start": 0.0, "end": 12.4, "speaker": "alice"},
  {"start": 12.4, "end": 31.0, "speaker": "bob"}
]
```

The `speaker` value should match the X handle without requiring `@`.

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
- requests
- Pillow
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
│   ├── x_api.py         # X GraphQL metadata client
│   ├── video.py         # MP4 participant-view renderer
│   ├── models.py        # Shared data models
│   └── validator.py     # URL validation
├── tests/
│   ├── test_main.py
│   ├── test_downloader.py
│   ├── test_video.py
│   ├── test_x_api.py
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
