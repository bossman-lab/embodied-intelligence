from __future__ import annotations

import os
import urllib.request
from pathlib import Path


REPO_URL = "https://huggingface.co/datasets/Datawhale/tuntunclaw-assets/resolve/main"

FILES = [
    "assets/fig.png",
    "manipulator_grasp/assets/target_basket_medium/materials/textures/texture.png",
    "manipulator_grasp/assets/libero_basket/texture.png",
]


def download_file(rel_path: str, root: Path) -> None:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(f"{REPO_URL}/{rel_path}")
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    print(f"Downloading {rel_path}")
    with urllib.request.urlopen(request) as response, target.open("wb") as output:
        output.write(response.read())


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    for rel_path in FILES:
        download_file(rel_path, root)
    print("Large assets are ready.")


if __name__ == "__main__":
    main()
