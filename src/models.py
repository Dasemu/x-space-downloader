from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Participant:
    """A user visible in the Space participant tray."""

    user_id: str
    display_name: str
    username: str
    avatar_url: Optional[str] = None
    role: str = "speaker"


@dataclass(frozen=True)
class SpaceMetadata:
    """Metadata needed to render a Space replay video."""

    space_id: str
    title: str
    participants: List[Participant] = field(default_factory=list)
    media_key: Optional[str] = None
    started_at_ms: Optional[int] = None
    ended_at_ms: Optional[int] = None


@dataclass(frozen=True)
class SpeakerInterval:
    """An interval where a known participant is speaking."""

    start: float
    end: float
    speaker: str
