import json

from src.x_api import build_timeline_from_history, parse_audio_space_metadata


def test_parse_audio_space_metadata_extracts_title_creator_and_speakers():
    payload = {
        "data": {
            "audioSpace": {
                "metadata": {
                    "rest_id": "1ZkKzZWnVRRKv",
                    "title": "Example Space",
                    "media_key": "28_123",
                    "creator_results": {
                        "result": {
                            "rest_id": "10",
                            "legacy": {
                                "name": "Host User",
                                "screen_name": "host",
                                "profile_image_url_https": "https://example.com/host.jpg",
                            },
                        }
                    },
                },
                "participants": {
                    "speakers": [
                        {
                            "display_name": "Speaker User",
                            "twitter_screen_name": "speaker",
                            "avatar_url": "https://example.com/speaker.jpg",
                            "periscope_user_id": "20",
                        }
                    ]
                },
            }
        }
    }

    metadata = parse_audio_space_metadata(payload, "1ZkKzZWnVRRKv")

    assert metadata.title == "Example Space"
    assert metadata.media_key == "28_123"
    assert [participant.username for participant in metadata.participants] == ["host", "speaker"]
    assert metadata.participants[0].role == "host"
    assert metadata.participants[1].role == "speaker"


def test_build_timeline_uses_unmute_mute_events_not_captions():
    start_ms = 1_000_000
    messages = [
        _history_message("alice", 17, start_ms + 5_000),
        _caption_message("bob", start_ms + 6_000),
        _history_message("alice", 16, start_ms + 12_000),
    ]

    intervals, first_seen, participants = build_timeline_from_history(messages, start_ms)

    assert len(intervals) == 1
    assert intervals[0].speaker == "alice"
    assert intervals[0].start == 5
    assert intervals[0].end == 12
    assert first_seen == {"alice": 5}
    assert {participant.username for participant in participants} == {"alice", "bob"}


def _history_message(username, event, timestamp_ms):
    payload = {
        "body": json.dumps({
            "guestBroadcastingEvent": event,
            "guestRemoteID": username,
            "guestUsername": username,
            "type": 40,
        }),
        "timestamp": timestamp_ms * 1_000_000,
    }
    return {"payload": json.dumps(payload)}


def _caption_message(username, timestamp_ms):
    payload = {
        "body": json.dumps({
            "type": 45,
            "username": username,
            "displayName": username.title(),
            "timestamp": timestamp_ms,
        }),
        "timestamp": timestamp_ms * 1_000_000,
    }
    return {"payload": json.dumps(payload)}
