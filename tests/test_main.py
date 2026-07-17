import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock
from src.main import cli
from src.downloader import DownloadError


def test_cli_valid_url(tmp_path):
    """Test CLI with valid URL."""
    runner = CliRunner()

    with patch('src.main.validate_space_url') as mock_validate, \
         patch('src.main.download_space') as mock_download:

        mock_validate.return_value = (True, "1ZkKzZWnVRRKv", None)
        mock_download.return_value = str(tmp_path / "space_1ZkKzZWnVRRKv.mp3")

        result = runner.invoke(cli, ['https://x.com/i/spaces/1ZkKzZWnVRRKv', '--mode', 'audio'])

        assert result.exit_code == 0
        assert "Successfully downloaded" in result.output
        assert "space_1ZkKzZWnVRRKv.mp3" in result.output


def test_cli_invalid_url():
    """Test CLI with invalid URL."""
    runner = CliRunner()

    result = runner.invoke(cli, ['https://invalid.com/spaces/123'])

    assert result.exit_code == 1
    assert "Invalid URL format" in result.output


def test_cli_download_failure():
    """Test CLI when download fails."""
    runner = CliRunner()

    with patch('src.main.validate_space_url') as mock_validate, \
         patch('src.main.download_space') as mock_download:

        mock_validate.return_value = (True, "1ZkKzZWnVRRKv", None)
        mock_download.side_effect = DownloadError("Video unavailable")

        result = runner.invoke(cli, ['https://x.com/i/spaces/1ZkKzZWnVRRKv', '--mode', 'audio'])

        assert result.exit_code == 2
        assert "Video unavailable" in result.output


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
            '--cookies', str(cookies_file),
            '--mode', 'audio',
        ])

        assert result.exit_code == 0
        # Verify the call was made with correct arguments including cookies_file
        mock_download.assert_called_once_with(
            'https://x.com/i/spaces/1ZkKzZWnVRRKv',
            '.',
            str(cookies_file)
        )


def test_cli_video_mode(tmp_path):
    """Test CLI default video mode."""
    runner = CliRunner()

    with patch('src.main.validate_space_url') as mock_validate, \
         patch('src.main.download_space_video') as mock_download:

        mock_validate.return_value = (True, "1ZkKzZWnVRRKv", None)
        mock_download.return_value = str(tmp_path / "space_1ZkKzZWnVRRKv.mp4")

        result = runner.invoke(cli, ['https://x.com/i/spaces/1ZkKzZWnVRRKv'])

        assert result.exit_code == 0
        assert "space_1ZkKzZWnVRRKv.mp4" in result.output
        mock_download.assert_called_once_with(
            'https://x.com/i/spaces/1ZkKzZWnVRRKv',
            '.',
            None,
            None,
            None,
        )
