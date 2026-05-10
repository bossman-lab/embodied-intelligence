"""Simple JSONL memory for agent interactions."""

import json
from datetime import datetime
from pathlib import Path


class MemoryStore:
    def __init__(self, root: str = "temp/openclaw_memory") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "events.jsonl"

    def append(self, payload: dict) -> None:
        data = {
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            **payload,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
