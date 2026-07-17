import click
from click.exceptions import Exit
from src.validator import validate_space_url
from src.downloader import download_space, download_space_video, DownloadError


@click.command()
@click.argument('url')
@click.option('--cookies', '-c', type=click.Path(exists=True), help='Path to cookies file')
@click.option('--output', '-o', type=click.Path(), default='.', help='Output directory')
@click.option(
    '--mode',
    type=click.Choice(['audio', 'video']),
    default='video',
    show_default=True,
    help='Output type to generate',
)
@click.option(
    '--speaker-timeline',
    type=click.Path(exists=True),
    help='JSON file with speaker intervals: [{"start": 0, "end": 5, "speaker": "handle"}]',
)
@click.option(
    '--max-duration',
    type=float,
    hidden=True,
    help='Render only the first N seconds; intended for tests and previews',
)
def cli(url, cookies, output, mode, speaker_timeline, max_duration):
    """
    Download X (Twitter) Space recordings as MP3 or MP4 files.

    Example:
        x-space-dl https://x.com/i/spaces/1ZkKzZWnVRRKv
    """
    # Validate URL
    is_valid, space_id, error = validate_space_url(url)
    if not is_valid:
        click.echo(f"Error: {error}", err=True)
        raise Exit(1)

    # Download the Space
    try:
        click.echo(f"Downloading Space: {space_id}")
        if mode == 'audio':
            output_path = download_space(url, output, cookies)
        else:
            output_path = download_space_video(url, output, cookies, speaker_timeline, max_duration)
        click.echo(f"Successfully downloaded to: {output_path}")
    except DownloadError as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise Exit(2)


if __name__ == '__main__':
    cli()
