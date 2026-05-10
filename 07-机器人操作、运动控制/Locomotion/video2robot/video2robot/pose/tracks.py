"""Utilities for handling multi-person SMPL-X tracks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TrackInfo:
    """Metadata describing a single SMPL-X track."""

    index: int
    smplx_path: Path
    track_id: Optional[str] = None
    metadata: Dict = None

    def exists(self) -> bool:
        return self.smplx_path.exists()


def _load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def load_smplx_track_metadata(project_dir: Path, base_name: str = "smplx") -> dict:
    """Load SMPL-X track metadata dictionary if available."""
    meta_path = Path(project_dir) / f"{base_name}_tracks.json"
    if not meta_path.exists():
        return {}
    return _load_json(meta_path)


def get_smplx_tracks(project_dir: Path, base_name: str = "smplx") -> List[TrackInfo]:
    """Return ordered SMPL-X tracks for a project."""
    project_dir = Path(project_dir)
    meta = load_smplx_track_metadata(project_dir, base_name=base_name)
    tracks: list[TrackInfo] = []

    if meta:
        for default_idx, track in enumerate(meta.get("tracks", []), start=1):
            idx = int(track.get("index", default_idx))
            filename = track.get("output", f"{base_name}_track_{idx}.npz")
            track_path = project_dir / filename
            tracks.append(
                TrackInfo(
                    index=idx,
                    smplx_path=track_path,
                    track_id=track.get("track_id"),
                    metadata=track,
                )
            )

    if not tracks:
        for track_path in sorted(project_dir.glob(f"{base_name}_track_*.npz")):
            name = track_path.stem
            try:
                suffix = name.split("_track_")[-1]
                idx = int(suffix)
            except (IndexError, ValueError):
                continue
            tracks.append(TrackInfo(index=idx, smplx_path=track_path))

    if not tracks:
        default = project_dir / f"{base_name}.npz"
        if default.exists():
            tracks.append(TrackInfo(index=1, smplx_path=default))

    # Ensure deterministic order and deduplicate indexes.
    tracks.sort(key=lambda info: info.index)
    seen = set()
    deduped: list[TrackInfo] = []
    for track in tracks:
        if track.index in seen:
            continue
        seen.add(track.index)
        deduped.append(track)
    return deduped


def get_track_by_index(tracks: List[TrackInfo], index: int) -> Optional[TrackInfo]:
    """Return TrackInfo with the given index, if available."""
    for track in tracks:
        if track.index == index:
            return track
    return None
