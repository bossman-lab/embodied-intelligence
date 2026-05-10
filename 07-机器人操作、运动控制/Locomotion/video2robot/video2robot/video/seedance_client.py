"""Seedance API video generation client."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import requests

from video2robot.utils import emit_progress


class SeedanceClient:
    """Seedance video generation client.

    API:
      - POST /generate
      - GET  /status?task_id=...
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://seedanceapi.org/v1",
    ):
        self.api_key = api_key or os.environ.get("SEEDANCE_API_KEY")
        if not self.api_key:
            raise ValueError("SEEDANCE_API_KEY required. Set env or pass api_key.")
        self.base_url = base_url.rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(
        self,
        prompt: str,
        output_path: str,
        *,
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
        duration_seconds: int = 8,
        poll_interval: int = 10,
        max_wait_time: int = 600,
    ) -> str:
        print("[Seedance] Creating video task...")
        emit_progress("init", 0.05, "初始化中")

        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "duration": str(duration_seconds),
        }
        resp = requests.post(
            f"{self.base_url}/generate",
            headers=self._headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Seedance generate failed: {resp.status_code} - {resp.text}")

        data = resp.json()
        task_id = ((data.get("data") or {}).get("task_id"))
        if not task_id:
            raise RuntimeError(f"Seedance response missing task_id: {data}")

        emit_progress("api_request", 0.10, "任务已提交")
        print(f"[Seedance] Task: {task_id}")

        video_url = self._poll_status(task_id, poll_interval=poll_interval, max_wait_time=max_wait_time)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._download_video(video_url, output)
        emit_progress("done", 1.0, "完成")
        print(f"[Seedance] Saved: {output}")
        return str(output)

    def _poll_status(self, task_id: str, *, poll_interval: int, max_wait_time: int) -> str:
        start = time.time()
        while True:
            elapsed = time.time() - start
            if elapsed > max_wait_time:
                raise TimeoutError(f"Seedance timed out after {max_wait_time}s")

            resp = requests.get(
                f"{self.base_url}/status",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"task_id": task_id},
                timeout=60,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Seedance status failed: {resp.status_code} - {resp.text}")

            payload = resp.json().get("data") or {}
            status = str(payload.get("status", "")).upper()
            if status == "SUCCESS":
                urls = payload.get("response") or []
                if not urls:
                    raise RuntimeError("Seedance success without video URL")
                emit_progress("download", 0.90, "下载中")
                return str(urls[0])
            if status == "FAILED":
                raise RuntimeError(f"Seedance failed: {payload.get('error_message')}")

            ratio = min(elapsed / 120.0, 1.0)
            emit_progress("generating", 0.10 + 0.75 * ratio, f"生成中（{int(elapsed)}s）")
            time.sleep(poll_interval)

    def _download_video(self, url: str, output_path: Path) -> None:
        resp = requests.get(url, stream=True, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"Video download failed: {resp.status_code} - {url}")
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
