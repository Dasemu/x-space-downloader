import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont

from src.models import Participant, SpaceMetadata, SpeakerInterval


class RenderError(Exception):
    """Raised when the MP4 render fails."""


class SpeakerTimeline:
    """Lookup table for active speakers during a replay."""

    def __init__(self, intervals: Iterable[SpeakerInterval], participant_first_seen: Optional[Dict[str, float]] = None):
        self.intervals = sorted(intervals, key=lambda item: item.start)
        self.participant_first_seen = {
            username.lstrip("@").lower(): float(seconds)
            for username, seconds in (participant_first_seen or {}).items()
        }

    @classmethod
    def from_file(cls, path: str) -> "SpeakerTimeline":
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        return cls.from_file_data(payload)

    @classmethod
    def from_file_data(cls, payload) -> "SpeakerTimeline":
        rows = payload.get("speakers", payload) if isinstance(payload, dict) else payload
        intervals = []
        for row in rows:
            intervals.append(
                SpeakerInterval(
                    start=float(row["start"]),
                    end=float(row["end"]),
                    speaker=str(row.get("speaker") or row.get("username") or row.get("handle")),
                )
            )
        return cls(intervals)

    def active_at(self, seconds: float) -> Optional[str]:
        active = self.active_speakers_at(seconds)
        return active[0] if active else None

    def active_speakers_at(self, seconds: float) -> List[str]:
        return [
            interval.speaker.lstrip("@").lower()
            for interval in self.intervals
            if interval.start <= seconds < interval.end
        ]

    def first_seen_at(self, username: str) -> Optional[float]:
        return self.participant_first_seen.get(username.lstrip("@").lower())


def render_space_video(
    audio_path: str,
    output_path: str,
    metadata: SpaceMetadata,
    timeline: Optional[SpeakerTimeline] = None,
    width: int = 720,
    height: int = 720,
    fps: int = 1,
    max_duration: Optional[float] = None,
) -> str:
    """Render an MP4 that mimics the compact X Spaces participant view."""
    if not os.path.exists(audio_path):
        raise RenderError(f"Audio file not found: {audio_path}")
    if shutil.which("ffmpeg") is None:
        raise RenderError("ffmpeg is required to render the video")

    duration = max_duration or probe_duration(audio_path)
    if duration <= 0:
        raise RenderError("Could not determine audio duration")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    avatars = load_avatars(metadata.participants, avatar_size=168)

    if timeline is None:
        frame = render_frame(metadata, avatars, None, 0, width, height)
        return render_looped_image_video(frame, audio_path, str(output), duration)

    command = build_ffmpeg_command(audio_path, str(output), width, height, fps)

    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        total_frames = max(1, int(math.ceil(duration * fps)))
        frame_cache: Dict[Tuple[Tuple[str, ...], Optional[str], int], bytes] = {}
        for frame_index in range(total_frames):
            seconds = frame_index / fps
            participants = visible_participants(metadata.participants, timeline, seconds)
            active = tuple(timeline.active_speakers_at(seconds)) if timeline else ()
            cache_key = (tuple(participant.username.lower() for participant in participants), active)
            frame_bytes = frame_cache.get(cache_key)
            if frame_bytes is None:
                frame = render_frame(
                    replace(metadata, participants=participants),
                    avatars,
                    timeline,
                    seconds,
                    width,
                    height,
                    participants_are_filtered=True,
                )
                frame_bytes = frame.tobytes()
                frame_cache[cache_key] = frame_bytes
            process.stdin.write(frame_bytes)
    except BrokenPipeError as exc:
        raise RenderError("ffmpeg closed before all frames were written") from exc
    finally:
        if process.stdin:
            process.stdin.close()

    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        raise RenderError(stderr.strip() or "ffmpeg failed")

    return str(output)


def render_looped_image_video(frame: Image.Image, audio_path: str, output_path: str, duration: float) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        frame_path = handle.name
    try:
        frame.save(frame_path)
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-framerate",
            "1",
            "-i",
            frame_path,
            "-i",
            audio_path,
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-shortest",
            output_path,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RenderError(result.stderr.strip() or "ffmpeg failed")
        return output_path
    finally:
        try:
            os.unlink(frame_path)
        except FileNotFoundError:
            pass


def build_ffmpeg_command(audio_path: str, output_path: str, width: int, height: int, fps: int) -> List[str]:
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-s",
        f"{width}x{height}",
        "-pix_fmt",
        "rgb24",
        "-r",
        str(fps),
        "-i",
        "-",
        "-i",
        audio_path,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
            "-c:a",
            "copy",
        "-shortest",
        output_path,
    ]


def probe_duration(path: str) -> float:
    if shutil.which("ffprobe") is None:
        raise RenderError("ffprobe is required to inspect audio duration")

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RenderError(result.stderr.strip() or "ffprobe failed")
    return float(result.stdout.strip())


def load_avatars(participants: List[Participant], avatar_size: int) -> Dict[str, Image.Image]:
    avatars: Dict[str, Image.Image] = {}
    for participant in participants:
        image = None
        if participant.avatar_url:
            try:
                response = requests.get(participant.avatar_url, timeout=8)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content)).convert("RGB")
            except Exception:
                image = None

        if image is None:
            image = placeholder_avatar(participant, avatar_size)
        avatars[participant.username.lower()] = crop_circle(image, avatar_size)
    return avatars


def render_frame(
    metadata: SpaceMetadata,
    avatars: Dict[str, Image.Image],
    timeline: Optional[SpeakerTimeline],
    seconds: float,
    width: int,
    height: int,
    participants_are_filtered: bool = False,
) -> Image.Image:
    participants = metadata.participants if participants_are_filtered else visible_participants(metadata.participants, timeline, seconds)
    active = set(timeline.active_speakers_at(seconds)) if timeline else set()

    frame = Image.new("RGB", (width, height), (18, 21, 24))
    draw = ImageDraw.Draw(frame)
    fonts = load_fonts()

    draw_rounded_rectangle(draw, (24, 24, width - 24, height - 24), 28, fill=(9, 13, 17), outline=(39, 46, 54))
    draw.text((54, 54), truncate(metadata.title, 42), fill=(238, 242, 246), font=fonts["title"])
    subtitle = "X Space replay"
    if timeline and timeline.intervals:
        subtitle += " · speaker timeline"
    draw.text((54, 92), subtitle, fill=(139, 152, 165), font=fonts["small"])

    if not participants:
        participants = [Participant("space", "Space audio", "space", role="speaker")]

    layout = participant_layout(width, height, len(participants))
    for participant, box in zip(participants, layout):
        draw_participant(frame, draw, participant, avatars.get(participant.username.lower()), box, active, seconds, fonts)

    return frame


def visible_participants(
    participants: List[Participant],
    timeline: Optional[SpeakerTimeline] = None,
    seconds: float = 0,
) -> List[Participant]:
    primary = [item for item in participants if item.role in {"host", "speaker"}]
    if not primary:
        primary = participants

    if not timeline or not timeline.participant_first_seen:
        return primary[:10]

    active = set(timeline.active_speakers_at(seconds))
    visible = []
    for participant in primary:
        first_seen = timeline.first_seen_at(participant.username)
        if participant.role == "host" or first_seen is None and participant.username.lower() in active:
            first_seen = 0
        if first_seen is not None and first_seen <= seconds:
            visible.append((first_seen, participant))

    visible.sort(key=lambda item: (item[0], item[1].username.lower()))
    selected = [item[1] for item in visible[-10:]]
    for active_username in active:
        if all(item.username.lower() != active_username for item in selected):
            active_participant = next((item for item in primary if item.username.lower() == active_username), None)
            if active_participant:
                selected = (selected + [active_participant])[-10:]
    return selected


def participant_layout(width: int, height: int, count: int) -> List[Tuple[int, int, int, int]]:
    top = 142
    bottom = height - 28
    area_width = width - 88
    area_height = bottom - top

    columns = 1 if count == 1 else 2
    rows = int(math.ceil(count / columns))
    cell_width = area_width // columns
    cell_height = area_height // rows

    boxes = []
    for index in range(count):
        col = index % columns
        row = index // columns
        x1 = 44 + col * cell_width
        y1 = top + row * cell_height
        x2 = x1 + cell_width - 18
        y2 = y1 + cell_height - 10
        boxes.append((x1, y1, x2, y2))
    return boxes


def draw_participant(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    participant: Participant,
    avatar: Optional[Image.Image],
    box: Tuple[int, int, int, int],
    active: Set[str],
    seconds: float,
    fonts: Dict[str, ImageFont.ImageFont],
) -> None:
    x1, y1, x2, y2 = box
    is_active = participant.username.lower() in active
    fill = (25, 30, 35) if not is_active else (20, 38, 34)
    outline = (52, 63, 73) if not is_active else (29, 155, 120)
    draw_rounded_rectangle(draw, box, 20, fill=fill, outline=outline, width=3 if is_active else 1)

    cell_height = y2 - y1
    avatar_size = min(118, max(44, int(cell_height * 0.42)))
    avatar_x = x1 + ((x2 - x1) - avatar_size) // 2
    avatar_y = y1 + max(8, int(cell_height * 0.08))
    if avatar is None:
        avatar = placeholder_avatar(participant, avatar_size)
    resized_avatar = avatar.resize((avatar_size, avatar_size))
    frame.paste(resized_avatar, (avatar_x, avatar_y), resized_avatar.getchannel("A"))

    if is_active:
        pulse = 7
        draw.ellipse(
            (
                avatar_x - pulse,
                avatar_y - pulse,
                avatar_x + avatar_size + pulse,
                avatar_y + avatar_size + pulse,
            ),
            outline=(29, 155, 120),
            width=4,
        )

    text_y = avatar_y + avatar_size + 6
    text_width = max(24, (x2 - x1) - 22)
    name = ellipsize(draw, participant.display_name, fonts["name"], text_width)
    username = ellipsize(draw, f"@{participant.username}", fonts["small"], text_width)
    draw_centered_text(draw, name, (x1 + 10, text_y, x2 - 10, text_y + 22), fonts["name"], (238, 242, 246))
    draw_centered_text(draw, username, (x1 + 10, text_y + 22, x2 - 10, text_y + 40), fonts["small"], (139, 152, 165))

    if is_active:
        badge = "Speaking"
        text_width = draw.textlength(badge, font=fonts["small"])
        badge_box = (x1 + 12, y1 + 10, x1 + int(text_width) + 34, y1 + 36)
        draw_rounded_rectangle(draw, badge_box, 14, fill=(29, 155, 120))
        draw.text((badge_box[0] + 13, badge_box[1] + 6), badge, fill=(3, 18, 14), font=fonts["small"])


def placeholder_avatar(participant: Participant, size: int) -> Image.Image:
    colors = [(29, 155, 240), (249, 24, 128), (255, 212, 0), (120, 86, 255), (0, 186, 124)]
    index = sum(ord(char) for char in participant.username) % len(colors)
    image = Image.new("RGB", (size, size), colors[index])
    draw = ImageDraw.Draw(image)
    font = load_fonts()["initial"]
    initial = (participant.display_name or participant.username or "?")[0].upper()
    bbox = draw.textbbox((0, 0), initial, font=font)
    draw.text(((size - (bbox[2] - bbox[0])) / 2, (size - (bbox[3] - bbox[1])) / 2 - 6), initial, fill=(255, 255, 255), font=font)
    return crop_circle(image, size)


def crop_circle(image: Image.Image, size: int) -> Image.Image:
    source = image.convert("RGB").resize((size, size))
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(source, (0, 0), mask)
    return output


def load_fonts() -> Dict[str, ImageFont.ImageFont]:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    regular = next((path for path in candidates if os.path.exists(path)), None)
    bold = next((path for path in bold_candidates if os.path.exists(path)), regular)
    return {
        "title": ImageFont.truetype(bold, 28) if bold else ImageFont.load_default(),
        "name": ImageFont.truetype(bold, 16) if bold else ImageFont.load_default(),
        "small": ImageFont.truetype(regular, 13) if regular else ImageFont.load_default(),
        "initial": ImageFont.truetype(bold, 64) if bold else ImageFont.load_default(),
    }


def draw_centered_text(draw: ImageDraw.ImageDraw, text: str, box: Tuple[int, int, int, int], font, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    x = box[0] + ((box[2] - box[0]) - (bbox[2] - bbox[0])) / 2
    y = box[1] + ((box[3] - box[1]) - (bbox[3] - bbox[1])) / 2
    draw.text((x, y), text, fill=fill, font=font)


def draw_rounded_rectangle(draw: ImageDraw.ImageDraw, box, radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1] + "..."


def ellipsize(draw: ImageDraw.ImageDraw, value: str, font, max_width: int) -> str:
    if draw.textlength(value, font=font) <= max_width:
        return value
    suffix = "..."
    trimmed = value
    while trimmed and draw.textlength(trimmed + suffix, font=font) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed or value[:1]) + suffix


def format_time(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"
