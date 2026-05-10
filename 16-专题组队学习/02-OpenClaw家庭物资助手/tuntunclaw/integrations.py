"""External integrations used by the OpenClaw demo."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _load_openclaw_config() -> dict[str, Any]:
    candidates = [
        Path(_env("OPENCLAW_CONFIG_PATH")) if _env("OPENCLAW_CONFIG_PATH") else None,
        Path.home() / ".openclaw" / "openclaw.json",
    ]
    for candidate in candidates:
        if candidate is None or not candidate.exists():
            continue
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


def _openclaw_feishu_block() -> dict[str, Any]:
    cfg = _load_openclaw_config()
    return dict(((cfg.get("channels") or {}).get("feishu") or {}))


def _request_json(
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=data, headers=headers or {}, method="POST" if payload is not None else "GET")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    if not raw:
        return {}
    return json.loads(raw)

@dataclass
class FeishuNotifier:
    app_id: str = ""
    app_secret: str = ""
    target: str = ""
    receive_id_type: str = "chat_id"
    enabled: bool = True
    token_ttl_seconds: int = 6600

    _tenant_token: str = ""
    _tenant_token_expiry: float = 0.0

    @classmethod
    def from_env(cls) -> "FeishuNotifier":
        feishu_cfg = _openclaw_feishu_block()
        app_id = _env("OPENCLAW_FEISHU_APP_ID") or str(feishu_cfg.get("appId") or "")
        app_secret = _env("OPENCLAW_FEISHU_APP_SECRET") or str(feishu_cfg.get("appSecret") or "")
        target = (
            _env("OPENCLAW_FEISHU_NOTIFY_TARGET")
            or _env("OPENCLAW_FEISHU_TARGET")
            or str(feishu_cfg.get("notifyTarget") or feishu_cfg.get("notify_target") or "")
        )
        receive_id_type = (
            _env("OPENCLAW_FEISHU_NOTIFY_RECEIVE_ID_TYPE")
            or _env("OPENCLAW_FEISHU_RECEIVE_ID_TYPE")
            or str(feishu_cfg.get("notifyReceiveIdType") or feishu_cfg.get("receiveIdType") or "chat_id")
        )
        enabled = _env("OPENCLAW_FEISHU_NOTIFY_ENABLED", "1").lower() not in {"0", "false", "no"}
        return cls(
            app_id=app_id,
            app_secret=app_secret,
            target=target,
            receive_id_type=receive_id_type or "chat_id",
            enabled=enabled,
        )

    def is_configured(self) -> bool:
        return bool(self.enabled and self.app_id and self.app_secret and self.target)

    def _tenant_access_token(self) -> str:
        if self._tenant_token and time.time() < self._tenant_token_expiry:
            return self._tenant_token

        if not self.app_id or not self.app_secret:
            raise RuntimeError("Feishu app credentials are missing")

        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        response = _request_json(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            payload=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        if int(response.get("code", 1)) != 0:
            raise RuntimeError(response.get("msg") or "failed to acquire tenant access token")

        token = str(response.get("tenant_access_token") or "")
        if not token:
            raise RuntimeError("tenant access token missing in Feishu response")

        expires = int(response.get("expire") or self.token_ttl_seconds)
        self._tenant_token = token
        self._tenant_token_expiry = time.time() + max(60, expires - 60)
        return token

    def send_markdown(
        self,
        text: str,
        *,
        target: str | None = None,
        receive_id_type: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "reason": "feishu notifier not configured"}

        target_value = (target or self.target).strip()
        receive_type = (receive_id_type or self.receive_id_type).strip() or "chat_id"
        content = {
            "zh_cn": {
                "content": [[{"tag": "md", "text": text}]],
            }
        }
        token = self._tenant_access_token()
        response = _request_json(
            f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_type}",
            payload={
                "receive_id": target_value,
                "msg_type": "post",
                "content": json.dumps(content, ensure_ascii=False),
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        if int(response.get("code", 1)) != 0:
            raise RuntimeError(response.get("msg") or "failed to send feishu message")
        data = response.get("data") or {}
        return {
            "ok": True,
            "message_id": str(data.get("message_id") or ""),
            "chat_id": str(data.get("chat_id") or ""),
            "raw": response,
        }

    def send_low_stock_alert(self, event: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "reason": "feishu notifier not configured"}

        order_url = str(event.get("order_url") or "")
        quantity = int(event.get("reorder_qty") or 1)
        remaining = int(event.get("remaining") or 0)
        threshold = int(event.get("threshold") or 0)
        label = str(event.get("label") or event.get("sku") or "物资")
        command = str(event.get("command") or "")
        session_id = str(event.get("session_id") or "")
        body = "\n".join(
            [
                f"## 库存预警：{label} 低于阈值",
                "",
                f"- 当前剩余：{remaining}",
                f"- 预设阈值：{threshold}",
                f"- 建议补货：{quantity}",
            ]
            + ([f"- 来源命令：{command}"] if command else [])
            + ([f"- 会话 ID：{session_id}"] if session_id else [])
            + ([f"[一键下单]({order_url})"] if order_url else [])
        )
        return self.send_markdown(body)


def post_json(url: str, payload: dict[str, Any], *, timeout: float = 8.0) -> dict[str, Any]:
    response = _request_json(
        url,
        payload=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=timeout,
    )
    return response


def notify_robot_backend(payload: dict[str, Any]) -> dict[str, Any]:
    url = _env("OPENCLAW_ROBOT_WEBHOOK_URL")
    if not url:
        return {"ok": False, "reason": "robot webhook not configured"}
    try:
        response = post_json(url, payload)
        return {"ok": True, "response": response}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "reason": str(exc)}


@lru_cache(maxsize=1)
def get_feishu_notifier() -> FeishuNotifier:
    return FeishuNotifier.from_env()
