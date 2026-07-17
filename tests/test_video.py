import json

from src.models import Participant, SpaceMetadata
from src.video import SpeakerTimeline, build_ffmpeg_command, render_frame


def test_speaker_timeline_reads_active_speaker(tmp_path):
    timeline_file = tmp_path / "timeline.json"
    timeline_file.write_text(
        json.dumps([
            {"start": 0, "end": 2.5, "speaker": "alice"},
            {"start": 2.5, "end": 4, "speaker": "@bob"},
        ]),
        encoding="utf-8",
    )

    timeline = SpeakerTimeline.from_file(str(timeline_file))

    assert timeline.active_at(1) == "alice"
    assert timeline.active_at(3) == "bob"
    assert timeline.active_at(5) is None


def test_build_ffmpeg_command_uses_audio_and_raw_video():
    command = build_ffmpeg_command("audio.mp3", "out.mp4", 720, 720, 24)

    assert command[:2] == ["ffmpeg", "-y"]
    assert "audio.mp3" in command
    assert "out.mp4" in command
    assert "720x720" in command


def test_render_frame_returns_rgb_image():
    metadata = SpaceMetadata(
        space_id="1ZkKzZWnVRRKv",
        title="Example Space",
        participants=[
            Participant("1", "Alice", "alice", role="host"),
            Participant("2", "Bob", "bob", role="speaker"),
        ],
    )
    timeline = SpeakerTimeline.from_file_data([{"start": 0, "end": 10, "speaker": "bob"}])

    frame = render_frame(metadata, {}, timeline, 1.0, 720, 720)

    assert frame.mode == "RGB"
    assert frame.size == (720, 720)
