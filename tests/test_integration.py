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
            '--output', str(tmp_path),
            '--mode', 'audio',
        ])

        # Verify success
        assert result.exit_code == 0
        assert "Successfully downloaded" in result.output

        # Verify yt-dlp was called correctly
        mock_ytdl.extract_info.assert_called_once()
        call_args = mock_ytdl_class.call_args
        assert 'bestaudio' in call_args[0][0]['format']
        assert 'mp3' in call_args[0][0]['postprocessors'][0]['preferredcodec']
