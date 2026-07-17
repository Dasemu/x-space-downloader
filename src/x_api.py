import json
import os
from dataclasses import replace
from datetime import datetime
from http.cookiejar import MozillaCookieJar
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode

import requests

from src.models import Participant, SpaceMetadata, SpeakerInterval


DEFAULT_GRAPHQL_QUERY_IDS = (
    "DovcWBliWe-v2TCRGFtibA",
    "Uv5R_-Chxbn1FEkyUkSW2w",
    "FJoTSHMVF7fMhGLc2t9cog",
)

GRAPHQL_FEATURES = {
    "spaces_2022_h2_spaces_communities": True,
    "spaces_2022_h2_clipping": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
}


class XApiError(Exception):
    """Raised when X metadata cannot be fetched or parsed."""


def load_netscape_cookies(cookies_file: str) -> Dict[str, str]:
    """Load a Netscape cookies.txt file into a simple name/value mapping."""
    jar = MozillaCookieJar()
    jar.load(cookies_file, ignore_discard=True, ignore_expires=True)
    return {cookie.name: cookie.value for cookie in jar}


def cookie_header(cookies: Dict[str, str]) -> str:
    return "; ".join(f"{name}={value}" for name, value in cookies.items())


class XApiClient:
    """Minimal client for X web GraphQL metadata used by Spaces replays."""

    def __init__(
        self,
        cookies_file: Optional[str] = None,
        bearer_token: Optional[str] = None,
        query_ids: Iterable[str] = DEFAULT_GRAPHQL_QUERY_IDS,
        timeout: int = 20,
    ):
        self.cookies = load_netscape_cookies(cookies_file) if cookies_file else {}
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN")
        if not self.bearer_token:
            raise XApiError(
                "No X API bearer token available. Set the X_BEARER_TOKEN environment "
                "variable to a bearer token from x.com's web client (visible in browser "
                "devtools as the 'authorization: Bearer ...' header on requests to "
                "x.com/i/api)."
            )
        env_query_id = os.getenv("X_AUDIO_SPACE_QUERY_ID")
        self.query_ids = (env_query_id, *tuple(query_ids)) if env_query_id else tuple(query_ids)
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_space_metadata(self, space_id: str) -> SpaceMetadata:
        last_error: Optional[Exception] = None
        for query_id in self.query_ids:
            try:
                payload = self._get_audio_space_by_id(query_id, space_id)
                return parse_audio_space_metadata(payload, space_id)
            except Exception as exc:
                last_error = exc

        raise XApiError(f"Could not fetch Space metadata: {last_error}")

    def fetch_space_timeline(self, metadata: SpaceMetadata) -> Tuple[List[SpeakerInterval], Dict[str, float], List[Participant]]:
        if not metadata.media_key:
            raise XApiError("Space metadata does not include media_key")

        status = self.fetch_live_video_status(metadata.media_key)
        playlist_url = (status.get("source") or {}).get("location")
        start_ms = fetch_playlist_start_ms(playlist_url, self.session) if playlist_url else None
        if start_ms is None:
            start_ms = metadata.started_at_ms
        if start_ms is None:
            raise XApiError("Could not determine replay start time")

        end_ms = metadata.ended_at_ms
        if end_ms is None:
            end_ms = start_ms + int((status.get("duration") or 4 * 60 * 60) * 1000)

        access = self.access_chat(status.get("chatToken"))
        endpoint = access.get("replay_endpoint") or access.get("endpoint")
        access_token = access.get("replay_access_token") or access.get("access_token")
        if not endpoint or not access_token:
            raise XApiError("Chat access response did not include replay endpoint/token")

        messages = self.fetch_history_messages(endpoint, access_token, start_ms, end_ms)
        return build_timeline_from_history(messages, start_ms)

    def fetch_live_video_status(self, media_key: str) -> dict:
        url = f"https://x.com/i/api/1.1/live_video_stream/status/{media_key}"
        headers = self._x_headers()
        response = self.session.get(
            url,
            params={
                "client": "web",
                "use_syndication_guest_id": "false",
                "cookie_set_host": "x.com",
            },
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise XApiError(f"live_video_stream/status returned HTTP {response.status_code}")
        return response.json()

    def access_chat(self, chat_token: Optional[str]) -> dict:
        if not chat_token:
            raise XApiError("live_video_stream/status did not include chatToken")

        payload = {"chat_token": chat_token}
        urls = (
            "https://proxsee-cf.pscp.tv/api/v2/accessChat",
            "https://proxsee.pscp.tv/api/v2/accessChat",
            "https://proxsee.pscp.tv/api/v2/accessChatPublic",
        )
        last_error = None
        for url in urls:
            try:
                response = self.session.post(url, json=payload, headers=chat_headers(), timeout=self.timeout)
                if response.status_code < 400 and response.text:
                    return response.json()
                last_error = XApiError(f"{url} returned HTTP {response.status_code}")
            except Exception as exc:
                last_error = exc
        raise XApiError(f"Could not access chat replay: {last_error}")

    def fetch_history_messages(self, endpoint: str, access_token: str, start_ms: int, end_ms: int) -> List[dict]:
        url = endpoint.rstrip("/") + "/chatapi/v1/history"
        step_ns = 60 * 1_000_000_000
        cursor_ns = start_ms * 1_000_000
        end_ns = end_ms * 1_000_000
        seen_cursors = set()
        seen_messages = set()
        messages: List[dict] = []

        first_payload = self._history_page(url, access_token, "", None)
        messages.extend(unique_messages(first_payload.get("messages") or [], seen_messages))
        response_cursor = _to_int(first_payload.get("cursor"))
        if response_cursor and response_cursor > cursor_ns:
            cursor_ns = response_cursor

        while cursor_ns <= end_ns:
            if cursor_ns in seen_cursors:
                cursor_ns += step_ns
                continue
            seen_cursors.add(cursor_ns)
            payload = self._history_page(url, access_token, str(cursor_ns), None)
            page_messages = unique_messages(payload.get("messages") or [], seen_messages)
            messages.extend(page_messages)
            response_cursor = _to_int(payload.get("cursor"))
            if response_cursor and response_cursor > cursor_ns:
                cursor_ns = response_cursor
            else:
                cursor_ns += step_ns

        return messages

    def _history_page(self, url: str, access_token: str, cursor: str, since: Optional[int]) -> dict:
        response = self.session.post(
            url,
            json={
                "access_token": access_token,
                "cursor": cursor,
                "limit": 1000,
                "since": since,
                "quick_get": True,
            },
            headers=chat_headers(),
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise XApiError(f"history returned HTTP {response.status_code}")
        return response.json()

    def _x_headers(self) -> Dict[str, str]:
        headers = {
            "accept": "*/*",
            "authorization": f"Bearer {self.bearer_token}",
            "content-type": "application/json",
            "referer": "https://x.com/",
            "user-agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            ),
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
        }
        if self.cookies:
            headers["cookie"] = cookie_header(self.cookies)
        if self.cookies.get("ct0"):
            headers["x-csrf-token"] = self.cookies["ct0"]
        return headers

    def _get_audio_space_by_id(self, query_id: str, space_id: str) -> dict:
        variables = {
            "id": space_id,
            "isMetatagsQuery": False,
            "withReplays": True,
            "withListeners": True,
        }
        params = urlencode(
            {
                "variables": json.dumps(variables, separators=(",", ":")),
                "features": json.dumps(GRAPHQL_FEATURES, separators=(",", ":")),
            }
        )
        url = f"https://x.com/i/api/graphql/{query_id}/AudioSpaceById?{params}"
        headers = self._x_headers()

        response = self.session.get(url, headers=headers, timeout=self.timeout)
        if response.status_code >= 400:
            raise XApiError(f"X returned HTTP {response.status_code}")

        payload = response.json()
        if payload.get("errors"):
            raise XApiError(payload["errors"][0].get("message", "GraphQL error"))
        return payload


def parse_audio_space_metadata(payload: dict, space_id: str) -> SpaceMetadata:
    audio_space = payload.get("data", {}).get("audioSpace") or {}
    metadata = audio_space.get("metadata") or {}
    if not metadata:
        raise XApiError("AudioSpaceById response did not include metadata")

    title = metadata.get("title") or f"X Space {space_id}"
    participants = _extract_participants(audio_space)
    creator = _participant_from_user_result(metadata.get("creator_results"), "host")
    if creator:
        participants = _dedupe_participants([creator, *participants])

    return SpaceMetadata(
        space_id=metadata.get("rest_id") or space_id,
        title=title,
        participants=participants,
        media_key=metadata.get("media_key"),
        started_at_ms=_timestamp_to_ms(metadata.get("started_at") or metadata.get("scheduled_start")),
        ended_at_ms=_timestamp_to_ms(metadata.get("ended_at")),
    )


def chat_headers() -> Dict[str, str]:
    return {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://x.com",
        "referer": "https://x.com/",
        "user-agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        ),
        "x-periscope-user-agent": "Twitter/m5",
    }


def fetch_playlist_start_ms(playlist_url: str, session: requests.Session) -> Optional[int]:
    response = session.get(playlist_url, headers={"origin": "https://x.com", "referer": "https://x.com/"}, timeout=20)
    if response.status_code >= 400:
        return None
    for line in response.text.splitlines():
        if line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            return iso_to_ms(line.split(":", 1)[1].strip())
    return None


def build_timeline_from_history(messages: List[dict], start_ms: int) -> Tuple[List[SpeakerInterval], Dict[str, float], List[Participant]]:
    participant_first_seen: Dict[str, float] = {}
    participants: Dict[str, Participant] = {}
    open_microphones: Dict[str, float] = {}
    intervals: List[SpeakerInterval] = []

    for message in messages:
        decoded = decode_history_payload(message)
        if not decoded:
            continue

        body = decoded.get("body")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = None
        if not isinstance(body, dict):
            continue

        body_type = body.get("type")
        if body_type == 40:
            username = body.get("guestUsername")
            event_ms = ns_to_ms(decoded.get("timestamp"))
            if username and event_ms:
                username_key = username.lower()
                seconds = max(0.0, (event_ms - start_ms) / 1000)
                event = body.get("guestBroadcastingEvent")
                if event in {9, 17}:
                    participant_first_seen.setdefault(username_key, seconds)
                participants.setdefault(
                    username_key,
                    Participant(
                        user_id=str(body.get("guestRemoteID") or username),
                        display_name=str(username),
                        username=str(username),
                        role="speaker",
                    ),
                )
                if event == 17:
                    open_microphones[username_key] = seconds
                elif event == 16:
                    start = open_microphones.pop(username_key, None)
                    if start is not None and seconds > start:
                        intervals.append(SpeakerInterval(start=start, end=seconds, speaker=username_key))
        elif body_type == 45:
            username = body.get("username")
            event_ms = iso_to_ms(body.get("programDateTime")) or _to_int(body.get("timestamp"))
            if username and event_ms:
                participants.setdefault(
                    username.lower(),
                    Participant(
                        user_id=str(body.get("twitter_id") or body.get("user_id") or username),
                        display_name=str(body.get("displayName") or username),
                        username=str(username),
                        role="speaker",
                    ),
                )

    last_event_second = max((interval.end for interval in intervals), default=0)
    for username, start in open_microphones.items():
        if last_event_second > start:
            intervals.append(SpeakerInterval(start=start, end=last_event_second, speaker=username))

    return intervals, participant_first_seen, list(participants.values())


def unique_messages(messages: List[dict], seen: set) -> List[dict]:
    output = []
    for message in messages:
        key = message.get("signature") or message.get("payload")
        if key in seen:
            continue
        seen.add(key)
        output.append(message)
    return output


def decode_history_payload(message: dict) -> Optional[dict]:
    payload = message.get("payload")
    if not isinstance(payload, str):
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def iso_to_ms(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return int(datetime.fromisoformat(normalized).timestamp() * 1000)
    except ValueError:
        return None


def ns_to_ms(value) -> Optional[int]:
    number = _to_int(value)
    if number is None:
        return None
    return number // 1_000_000


def _extract_participants(audio_space: dict) -> List[Participant]:
    participants_section = audio_space.get("participants") or {}
    participants: List[Participant] = []

    for key, role in (("admins", "host"), ("speakers", "speaker"), ("listeners", "listener")):
        for item in participants_section.get(key) or []:
            participant = _participant_from_participant_item(item, role)
            if participant:
                participants.append(participant)

    return _dedupe_participants(participants)


def _participant_from_participant_item(item: dict, role: str) -> Optional[Participant]:
    username = item.get("twitter_screen_name")
    display_name = item.get("display_name") or username
    avatar_url = item.get("avatar_url")

    user_results = item.get("user_results") or {}
    user_id = user_results.get("rest_id") or item.get("periscope_user_id") or username
    user = _participant_from_user_result(user_results, role)
    if user:
        return replace(
            user,
            display_name=display_name or user.display_name,
            username=username or user.username,
            avatar_url=avatar_url or user.avatar_url,
            role=role,
        )

    if not user_id or not username:
        return None
    return Participant(
        user_id=str(user_id),
        display_name=str(display_name or username),
        username=str(username),
        avatar_url=avatar_url,
        role=role,
    )


def _participant_from_user_result(user_results: Optional[dict], role: str) -> Optional[Participant]:
    if not user_results:
        return None

    result = user_results.get("result") or user_results
    legacy = result.get("legacy") or {}
    core = result.get("core") or {}
    avatar = result.get("avatar") or {}

    username = legacy.get("screen_name") or core.get("screen_name")
    display_name = legacy.get("name") or core.get("name") or username
    avatar_url = legacy.get("profile_image_url_https") or avatar.get("image_url")
    user_id = result.get("rest_id") or user_results.get("rest_id") or result.get("id")

    if not user_id or not username:
        return None
    return Participant(
        user_id=str(user_id),
        display_name=str(display_name or username),
        username=str(username),
        avatar_url=avatar_url,
        role=role,
    )


def _dedupe_participants(participants: List[Participant]) -> List[Participant]:
    by_key: Dict[str, Participant] = {}
    role_rank = {"host": 3, "speaker": 2, "listener": 1}
    for participant in participants:
        key = participant.username.lower() or participant.user_id
        existing = by_key.get(key)
        if not existing or role_rank.get(participant.role, 0) > role_rank.get(existing.role, 0):
            by_key[key] = participant
    return list(by_key.values())


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _timestamp_to_ms(value) -> Optional[int]:
    number = _to_int(value)
    if number is None:
        return None
    if number > 10_000_000_000:
        return number
    return number * 1000
