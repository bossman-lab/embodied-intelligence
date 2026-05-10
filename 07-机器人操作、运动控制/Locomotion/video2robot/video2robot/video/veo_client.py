"""
Google Veo Video Generation Client

Usage:
    from video2robot.video import VeoClient

    client = VeoClient(api_key="...")
    video_path = client.generate("A person dancing", output_path="output.mp4")
"""

from __future__ import annotations

import os
import time
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv

from video2robot.utils import emit_progress

load_dotenv()


class VeoClient:
    """Google Veo Video Generation Client"""

    # Gemini API supported models (per documentation)
    SUPPORTED_MODELS = [
        # Veo 3.1 (Preview)
        "veo-3.1-generate-preview",
        "veo-3.1-fast-generate-preview",
        # Veo 3.0 (Stable)
        "veo-3.0-generate-001",
        "veo-3.0-fast-generate-001",
        # Veo 2.0 (Stable)
        "veo-2.0-generate-001",
    ]

    def __init__(
        self,
        api_key: str = None,
        model_id: str = "veo-3.1-generate-preview",
    ):
        """
        Initialize Veo Client

        Args:
            api_key: Google AI API key (can use GOOGLE_API_KEY env var)
            model_id: Veo model ID
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key.")
        self.model_id = model_id

    @property
    def _endpoint(self) -> str:
        return (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model_id}:predictLongRunning"
        )

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _encode_image(self, image_path: str) -> Dict[str, str]:
        """Encode image to base64"""
        path = Path(image_path)
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(path.suffix.lower(), "image/jpeg")

        with open(path, "rb") as f:
            image_bytes = f.read()

        return {
            "bytesBase64Encoded": base64.b64encode(image_bytes).decode("utf-8"),
            "mimeType": mime_type,
        }

    def generate(
        self,
        prompt: str,
        output_path: str,
        image_path: Optional[str] = None,
        aspect_ratio: str = "16:9",
        duration_seconds: int = 8,
        seed: Optional[int] = None,
        negative_prompt: Optional[str] = None,
        resolution: Optional[str] = None,
        person_generation: str = "allow_all",
        poll_interval: int = 10,
        max_wait_time: int = 600,
    ) -> Path:
        """
        Generate video using Veo

        Args:
            prompt: Text description of the video
            output_path: Path to save the generated video
            image_path: Optional input image for image-to-video
            aspect_ratio: "16:9" or "9:16"
            duration_seconds: Video duration (Veo2: 5-8, Veo3: 4/6/8)
            seed: Random seed for reproducibility
            negative_prompt: What NOT to include (e.g. "cartoon, blur, low quality")
            resolution: "720p" or "1080p" (Veo3+ only, 1080p requires 8s duration)
            person_generation: "allow_all" (default, text-to-video), "allow_adult" (image-to-video), "dont_allow"
            poll_interval: Seconds between status checks
            max_wait_time: Maximum seconds to wait

        Returns:
            Path to the generated video
        """
        # 1. Validate duration
        is_veo2 = "veo-2" in self.model_id
        valid_durations = [5, 6, 8] if is_veo2 else [4, 6, 8]
        if duration_seconds not in valid_durations:
            raise ValueError(
                f"Invalid duration {duration_seconds}s for {self.model_id}. "
                f"Allowed: {valid_durations}"
            )

        # 2. Auto-fix 1080p + duration != 8
        if resolution == "1080p" and duration_seconds != 8:
            print(f"[Veo] Warning: 1080p only supports 8s duration. Auto-adjusting from {duration_seconds}s to 8s.")
            duration_seconds = 8

        # 3. Auto-fix personGeneration for image-to-video
        if image_path and person_generation != "allow_adult":
            print(f"[Veo] Warning: Image-to-video only supports 'allow_adult'. Auto-adjusting from '{person_generation}'.")
            person_generation = "allow_adult"

        # Build request
        instance = {"prompt": prompt}
        if image_path:
            instance["image"] = self._encode_image(image_path)

        parameters = {
            "aspectRatio": aspect_ratio,
            "durationSeconds": duration_seconds,
            "sampleCount": 1,
            "personGeneration": person_generation,
        }
        if seed is not None:
            parameters["seed"] = seed
        if negative_prompt:
            parameters["negativePrompt"] = negative_prompt
        if resolution:
            parameters["resolution"] = resolution

        request_body = {
            "instances": [instance],
            "parameters": parameters,
        }

        print(f"[Veo] Starting video generation...")
        print(f"[Veo] Model: {self.model_id}")
        print(f"[Veo] Prompt: {prompt[:100]}...")
        emit_progress("init", 0.05, "Initializing")

        # Start operation
        response = requests.post(
            self._endpoint,
            headers=self._headers,
            json=request_body,
        )

        if response.status_code != 200:
            raise RuntimeError(f"API request failed: {response.status_code} - {response.text}")

        operation = response.json()
        operation_name = operation.get("name")

        if not operation_name:
            raise RuntimeError(f"No operation name in response: {operation}")

        print(f"[Veo] Operation started: {operation_name}")
        emit_progress("api_request", 0.10, "API request sent")

        # Poll for completion
        result = self._poll_operation(operation_name, poll_interval, max_wait_time)

        # Save video
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_video(result, str(output_path))

        return output_path

    def _poll_operation(
        self,
        operation_name: str,
        poll_interval: int = 10,
        max_wait_time: int = 600,
        expected_seconds: float = 60.0,
    ) -> Dict[str, Any]:
        """Poll operation until completion"""
        poll_url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}"
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time

            if elapsed > max_wait_time:
                raise TimeoutError(f"Operation timed out after {max_wait_time}s")

            response = requests.get(poll_url, headers=self._headers)

            if response.status_code != 200:
                raise RuntimeError(f"Poll failed: {response.status_code} - {response.text}")

            status = response.json()

            if status.get("done"):
                print(f"[Veo] Completed in {elapsed:.1f}s")
                emit_progress("download", 0.90, "Downloading")

                if "error" in status:
                    raise RuntimeError(f"Generation failed: {status['error']}")

                return status.get("response", {})

            # Progress: 0.10 to 0.85 based on elapsed time
            ratio = min(elapsed / expected_seconds, 1.0)
            progress = 0.10 + 0.75 * ratio
            emit_progress("generating", progress, f"Generating ({int(elapsed)}s)")

            print(f"[Veo] Waiting... ({elapsed:.0f}s)")
            time.sleep(poll_interval)

    def _save_video(self, result: Dict[str, Any], output_path: str):
        """Save generated video to file"""
        # Find video data in response
        video_data = None
        if result.get("generateVideoResponse", {}).get("generatedSamples"):
            video_data = result["generateVideoResponse"]["generatedSamples"][0].get("video", {})
        elif result.get("generatedVideos"):
            video_data = result["generatedVideos"][0].get("video", {})
        elif result.get("videos"):
            video_data = result["videos"][0]

        if not video_data:
            # Save raw response for debugging
            with open(output_path + ".json", "w") as f:
                json.dump(result, f, indent=2)
            raise RuntimeError(f"Unknown response format. Saved to {output_path}.json")

        # Handle different formats
        if "bytesBase64Encoded" in video_data:
            video_bytes = base64.b64decode(video_data["bytesBase64Encoded"])
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            print(f"[Veo] Saved: {output_path}")
            emit_progress("done", 1.0, "Done")

        elif "uri" in video_data:
            self._download_from_url(video_data["uri"], output_path)

        elif "gcsUri" in video_data:
            self._download_from_gcs(video_data["gcsUri"], output_path)

        else:
            raise RuntimeError(f"Unknown video format: {video_data.keys()}")

    def _download_from_url(self, url: str, output_path: str):
        """Download video from URL"""
        response = requests.get(url, headers=self._headers, stream=True)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[Veo] Saved: {output_path}")
            emit_progress("done", 1.0, "Done")
        else:
            raise RuntimeError(f"Download failed: {response.status_code}")

    def _download_from_gcs(self, gcs_uri: str, output_path: str):
        """Download file from GCS"""
        try:
            from google.cloud import storage

            parts = gcs_uri.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_name = parts[1] if len(parts) > 1 else ""

            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.download_to_filename(output_path)
            print(f"[Veo] Saved: {output_path}")
            emit_progress("done", 1.0, "Done")

        except ImportError:
            print(f"[Veo] google-cloud-storage not installed.")
            print(f"[Veo] Download manually: gsutil cp {gcs_uri} {output_path}")


# CLI support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate video using Google Veo")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
    parser.add_argument("--output", "-o", default="output.mp4", help="Output path")
    parser.add_argument("--image", "-i", help="Input image for image-to-video")
    parser.add_argument("--model", default="veo-3.1-generate-preview", help="Model ID")
    parser.add_argument("--aspect-ratio", default="16:9", choices=["16:9", "9:16"])
    parser.add_argument("--duration", type=int, default=8, help="Duration in seconds")
    parser.add_argument("--seed", type=int, help="Random seed")
    parser.add_argument("--negative", help="What NOT to include")
    parser.add_argument("--resolution", choices=["720p", "1080p"], help="Resolution")
    parser.add_argument("--person", default="allow_all", 
                        choices=["allow_all", "allow_adult", "dont_allow"])

    args = parser.parse_args()

    client = VeoClient(model_id=args.model)
    client.generate(
        prompt=args.prompt,
        output_path=args.output,
        image_path=args.image,
        aspect_ratio=args.aspect_ratio,
        duration_seconds=args.duration,
        seed=args.seed,
        negative_prompt=args.negative,
        resolution=args.resolution,
        person_generation=args.person,
    )

