"""OpenClaw-like session primitives."""

from dataclasses import dataclass, field
from datetime import datetime
import uuid


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now_iso)
    turns: int = 0

    def next_turn(self) -> int:
        self.turns += 1
        return self.turns
