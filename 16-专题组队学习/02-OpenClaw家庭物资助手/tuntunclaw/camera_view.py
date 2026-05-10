import json
from pathlib import Path


def view_config_path(scene_path: str | Path) -> Path:
    scene_path = Path(scene_path)
    return scene_path.with_name(scene_path.stem + ".view.json")


def load_view_config(scene_path: str | Path):
    config_path = view_config_path(scene_path)
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        lookat = data.get("lookat")
        if not isinstance(lookat, list) or len(lookat) != 3:
            return None
        return {
            "lookat": [float(v) for v in lookat],
            "azimuth": float(data["azimuth"]),
            "elevation": float(data["elevation"]),
            "distance": float(data["distance"]),
        }
    except Exception:
        return None


def save_view_config(
    scene_path: str | Path,
    *,
    lookat,
    azimuth: float,
    elevation: float,
    distance: float,
) -> Path:
    config_path = view_config_path(scene_path)
    payload = {
        "lookat": [float(v) for v in lookat],
        "azimuth": float(azimuth),
        "elevation": float(elevation),
        "distance": float(distance),
    }
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path
