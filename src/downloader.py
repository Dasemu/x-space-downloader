import os
from glob import glob
import yt_dlp
from typing import Optional
from src.validator import validate_space_url
from src.models import SpaceMetadata
from src.video import RenderError, SpeakerTimeline, render_space_video
from src.x_api import XApiClient, XApiError


class DownloadError(Exception):
    """Raised when download fails."""
    pass


def download_space(
    space_url: str,
    output_dir: str,
    cookies_file: Optional[str] = None,
    audio_format: str = "mp3",
) -> str:
    """
    Downloads X Space recording using yt-dlp.

    Args:
        space_url: URL of the X Space recording
        output_dir: Directory to save the MP3 file
        cookies_file: Optional path to cookies file for authentication
        audio_format: Audio container/codec to write

    Returns:
        Path to the downloaded MP3 file

    Raises:
        DownloadError: If download fails
    """
    # Extract space ID from URL using validator for robustness
    is_valid, space_id, error_message = validate_space_url(space_url)
    if not is_valid:
        raise ValueError(f"Invalid space URL: {error_message}")

    if space_id is None:
        raise ValueError("Could not extract space ID from URL")

    os.makedirs(output_dir, exist_ok=True)

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f'space_{space_id}.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
    }
    if audio_format != "native":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
        }]

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
    if audio_format == "native":
        return os.path.join(output_dir, f'space_{space_id}')
    return os.path.join(output_dir, f'space_{space_id}.{audio_format}')


def download_space_video(
    space_url: str,
    output_dir: str,
    cookies_file: Optional[str] = None,
    speaker_timeline_file: Optional[str] = None,
    max_duration: Optional[float] = None,
) -> str:
    """
    Download an X Space replay and render an MP4 participant view with audio.
    """
    is_valid, space_id, error_message = validate_space_url(space_url)
    if not is_valid:
        raise ValueError(f"Invalid space URL: {error_message}")
    if space_id is None:
        raise ValueError("Could not extract space ID from URL")

    metadata = fetch_required_metadata(space_id, cookies_file)
    timeline = SpeakerTimeline.from_file(speaker_timeline_file) if speaker_timeline_file else None
    if timeline is None:
        timeline = fetch_required_timeline(metadata, cookies_file)

    audio_path = download_space(space_url, output_dir, cookies_file, audio_format="native")
    if not os.path.exists(audio_path):
        candidates = sorted(glob(os.path.join(output_dir, f"space_{space_id}.*")))
        candidates = [path for path in candidates if not path.endswith(".mp4")]
        if not candidates:
            raise DownloadError("Downloaded audio file was not found")
        audio_path = candidates[0]
    output_path = os.path.join(output_dir, f"space_{space_id}.mp4")

    try:
        return render_space_video(
            audio_path=audio_path,
            output_path=output_path,
            metadata=metadata,
            timeline=timeline,
            max_duration=max_duration,
        )
    except RenderError as exc:
        raise DownloadError(f"Failed to render Space video: {exc}") from exc


def fetch_metadata_or_fallback(space_id: str, cookies_file: Optional[str]) -> SpaceMetadata:
    try:
        return XApiClient(cookies_file=cookies_file).fetch_space_metadata(space_id)
    except XApiError:
        return SpaceMetadata(space_id=space_id, title=f"X Space {space_id}", participants=[])


def fetch_required_metadata(space_id: str, cookies_file: Optional[str]) -> SpaceMetadata:
    try:
        return XApiClient(cookies_file=cookies_file).fetch_space_metadata(space_id)
    except XApiError as exc:
        hint = " Export logged-in X cookies and pass them with --cookies." if not cookies_file else ""
        raise DownloadError(f"Failed to fetch Space metadata.{hint} Details: {exc}") from exc


def fetch_required_timeline(metadata: SpaceMetadata, cookies_file: Optional[str]) -> SpeakerTimeline:
    if not cookies_file:
        raise DownloadError("Video mode requires --cookies to fetch the replay participant timeline.")
    try:
        intervals, first_seen, history_participants = XApiClient(cookies_file=cookies_file).fetch_space_timeline(metadata)
    except XApiError as exc:
        raise DownloadError(f"Failed to fetch Space replay timeline: {exc}") from exc
    merge_history_participants(metadata, history_participants)
    if not intervals and not first_seen:
        raise DownloadError("Space replay timeline did not include participant or microphone events.")
    return SpeakerTimeline(intervals, first_seen)


def fetch_timeline_or_none(metadata: SpaceMetadata, cookies_file: str) -> Optional[SpeakerTimeline]:
    try:
        intervals, first_seen, history_participants = XApiClient(cookies_file=cookies_file).fetch_space_timeline(metadata)
    except XApiError:
        return None
    merge_history_participants(metadata, history_participants)
    if not intervals and not first_seen:
        return None
    return SpeakerTimeline(intervals, first_seen)


def merge_history_participants(metadata: SpaceMetadata, history_participants) -> None:
    existing = {participant.username.lower() for participant in metadata.participants}
    for participant in history_participants:
        if participant.username.lower() not in existing:
            metadata.participants.append(participant)
            existing.add(participant.username.lower())
