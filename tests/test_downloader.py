import pytest
from unittest.mock import Mock, patch
from src.downloader import download_space, DownloadError


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


def test_download_space_with_cookies(tmp_path):
    """Test that cookies file is passed to yt-dlp when provided."""
    space_url = "https://x.com/i/spaces/1ZkKzZWnVRRKv"
    cookies_path = "/path/to/cookies.txt"

    with patch('src.downloader.yt_dlp.YoutubeDL') as mock_ytdl_class:
        # Mock the YoutubeDL instance
        mock_ytdl = Mock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        mock_ytdl.extract_info.return_value = {'id': '1ZkKzZWnVRRKv'}

        # Call download_space with cookies
        result = download_space(
            space_url=space_url,
            output_dir=str(tmp_path),
            cookies_file=cookies_path
        )

        # Verify YoutubeDL was initialized with correct options
        call_args = mock_ytdl_class.call_args[0][0]
        assert 'cookiefile' in call_args
        assert call_args['cookiefile'] == cookies_path


def test_download_space_ytdlp_configuration(tmp_path):
    """Test that yt-dlp is configured correctly with format, outtmpl, and postprocessors."""
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

        # Verify YoutubeDL was initialized with correct options
        call_args = mock_ytdl_class.call_args[0][0]

        # Check format
        assert call_args['format'] == 'bestaudio/best'

        # Check outtmpl contains the space_id
        assert 'outtmpl' in call_args
        assert 'space_1ZkKzZWnVRRKv' in call_args['outtmpl']

        # Check postprocessors for MP3 conversion
        assert 'postprocessors' in call_args
        assert len(call_args['postprocessors']) > 0
        assert call_args['postprocessors'][0]['key'] == 'FFmpegExtractAudio'
        assert call_args['postprocessors'][0]['preferredcodec'] == 'mp3'


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
