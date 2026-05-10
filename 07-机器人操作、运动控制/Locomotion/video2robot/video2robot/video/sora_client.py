"""OpenAI Sora video generation client."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

from video2robot.utils import emit_progress


class SoraClient:
    """OpenAI Sora video generation client.

    Usage:
        client = SoraClient(model_id="sora-2")
        client.generate(
            prompt="A person walking in a park",
            output_path="output.mp4",
            size="1280x720",
            duration_seconds=8,
        )
    """

    VALID_MODELS = ["sora-2", "sora-2-pro"]
    VALID_SIZES = ["720x1280", "1280x720", "1024x1792", "1792x1024"]
    VALID_DURATIONS = [4, 8, 12]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: str = "sora-2",
    ):
        """Initialize SoraClient.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            model_id: Sora model ID. "sora-2" (fast) or "sora-2-pro" (quality).
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY required. Set via api_key parameter or OPENAI_API_KEY environment variable."
            )

        if model_id not in self.VALID_MODELS:
            raise ValueError(f"Invalid model_id: {model_id}. Valid: {self.VALID_MODELS}")

        self.model_id = model_id
        self.client = OpenAI(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        output_path: str,
        *,
        size: str = "1280x720",
        duration_seconds: int = 8,
        poll_interval: float = 5.0,
        max_wait_time: float = 600.0,
    ) -> str:
        """Generate video from text prompt.

        Args:
            prompt: Text description of the video to generate.
            output_path: Path where the video will be saved.
            size: Video size. Options: "720x1280", "1280x720", "1024x1792", "1792x1024".
                  Default "1280x720" (16:9 landscape).
            duration_seconds: Video duration in seconds. Options: 4, 8, or 12.
            poll_interval: Seconds between status checks (default: 5.0).
            max_wait_time: Maximum wait time in seconds (default: 600.0 = 10 minutes).

        Returns:
            Path to the generated video file.

        Raises:
            ValueError: If invalid size or duration_seconds.
            TimeoutError: If video generation exceeds max_wait_time.
            RuntimeError: If video generation fails.
        """
        # Validate parameters
        if size not in self.VALID_SIZES:
            raise ValueError(f"Invalid size: {size}. Valid: {self.VALID_SIZES}")
        if duration_seconds not in self.VALID_DURATIONS:
            raise ValueError(f"Invalid duration: {duration_seconds}. Valid: {self.VALID_DURATIONS}")

        # Create video generation job
        print(f"[Sora] Creating video with {self.model_id}...")
        print(f"[Sora] Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print(f"[Sora] Size: {size}, Duration: {duration_seconds}s")
        emit_progress("init", 0.05, "Initializing")

        response = self.client.videos.create(
            model=self.model_id,
            prompt=prompt,
            size=size,
            seconds=str(duration_seconds),
        )
        video_id = response.id
        print(f"[Sora] Job created: {video_id}")
        emit_progress("api_request", 0.10, "API request sent")

        # Expected times: sora-2 ~120s, sora-2-pro ~240s
        expected_seconds = 240.0 if "pro" in self.model_id else 120.0

        # Poll for completion
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise TimeoutError(f"Video generation timed out after {max_wait_time}s")

            status = self.client.videos.retrieve(video_id)
            print(f"[Sora] Status: {status.status} ({elapsed:.0f}s)")

            if status.status == "completed":
                emit_progress("download", 0.90, "Downloading")
                break
            elif status.status == "failed":
                error_msg = getattr(status, "error", "Unknown error")
                raise RuntimeError(f"Video generation failed: {error_msg}")

            # Progress: 0.10 to 0.85 based on elapsed time
            ratio = min(elapsed / expected_seconds, 1.0)
            progress = 0.10 + 0.75 * ratio
            emit_progress("generating", progress, f"Generating ({int(elapsed)}s)")

            time.sleep(poll_interval)

        # Download video
        print(f"[Sora] Downloading video...")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        content = self.client.videos.download_content(video_id, variant="video")
        content.write_to_file(str(output))

        print(f"[Sora] Saved: {output_path}")
        emit_progress("done", 1.0, "Done")
        return str(output_path)
