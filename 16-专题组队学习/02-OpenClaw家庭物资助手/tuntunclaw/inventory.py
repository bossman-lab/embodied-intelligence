"""Persistent inventory tracking for the OpenClaw demo workflow."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _default_public_base() -> str:
    host = os.getenv("OPENCLAW_WEB_HOST", "127.0.0.1").strip()
    port = os.getenv("OPENCLAW_WEB_PORT", "8000").strip()
    return (
        os.getenv("OPENCLAW_PUBLIC_BASE_URL", "").strip()
        or os.getenv("OPENCLAW_WEB_PUBLIC_BASE_URL", "").strip()
        or f"http://{host}:{port}"
    )


@dataclass
class InventoryItem:
    key: str
    label: str
    count: int
    threshold: int
    reorder_qty: int
    unit: str = "块"
    alert_sent: bool = False
    order_pending: bool = False
    last_updated_at: str = ""
    last_alert_at: str = ""
    last_alert_token: str = ""
    last_order_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "count": self.count,
            "threshold": self.threshold,
            "reorder_qty": self.reorder_qty,
            "unit": self.unit,
            "alert_sent": self.alert_sent,
            "order_pending": self.order_pending,
            "last_updated_at": self.last_updated_at,
            "last_alert_at": self.last_alert_at,
            "last_alert_token": self.last_alert_token,
            "last_order_at": self.last_order_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InventoryItem":
        return cls(
            key=str(payload.get("key") or payload.get("sku") or "chocolate"),
            label=str(payload.get("label") or payload.get("label_zh") or "巧克力"),
            count=int(payload.get("count", 0)),
            threshold=int(payload.get("threshold", 3)),
            reorder_qty=int(payload.get("reorder_qty", 10)),
            unit=str(payload.get("unit") or "块"),
            alert_sent=bool(payload.get("alert_sent", False)),
            order_pending=bool(payload.get("order_pending", False)),
            last_updated_at=str(payload.get("last_updated_at") or ""),
            last_alert_at=str(payload.get("last_alert_at") or ""),
            last_alert_token=str(payload.get("last_alert_token") or ""),
            last_order_at=str(payload.get("last_order_at") or ""),
        )


class InventoryStore:
    """File-backed, thread-safe inventory and order tracker."""

    ALIASES = {
        "chocolate": [
            "chocolate",
            "choco",
            "chocolate bar",
            "巧克力",
            "巧克力棒",
            "巧克力块",
        ],
    }

    DEFAULT_ITEMS = {
        "chocolate": InventoryItem(
            key="chocolate",
            label="巧克力",
            count=12,
            threshold=3,
            reorder_qty=10,
            unit="块",
        ),
    }

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        public_base_url: str | None = None,
    ) -> None:
        self.root = Path(root) if root is not None else Path(__file__).resolve().parent / "temp" / "inventory"
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "inventory.json"
        self.orders_path = self.root / "orders.jsonl"
        self.public_base_url = (public_base_url or _default_public_base()).rstrip("/")
        self._lock = threading.RLock()
        self._state = self._load_state()
        self._processed_sessions: set[str] = set(self._state.get("processed_sessions", []))
        self._processed_order_tokens: set[str] = set(self._state.get("processed_order_tokens", []))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load_state(self) -> dict[str, Any]:
        if self.state_path.exists():
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
                items = {
                    key: InventoryItem.from_dict(value).to_dict()
                    for key, value in (raw.get("items") or {}).items()
                }
                if not items:
                    items = {key: item.to_dict() for key, item in self.DEFAULT_ITEMS.items()}
                return {
                    "items": items,
                    "history": list(raw.get("history") or []),
                    "alerts": list(raw.get("alerts") or []),
                    "orders": list(raw.get("orders") or []),
                    "processed_sessions": list(raw.get("processed_sessions") or []),
                    "processed_order_tokens": list(raw.get("processed_order_tokens") or []),
                    "updated_at": str(raw.get("updated_at") or _now_iso()),
                }
            except Exception:
                pass
        return {
            "items": {key: item.to_dict() for key, item in self.DEFAULT_ITEMS.items()},
            "history": [],
            "alerts": [],
            "orders": [],
            "processed_sessions": [],
            "processed_order_tokens": [],
            "updated_at": _now_iso(),
        }

    def _save_state(self) -> None:
        self._state["updated_at"] = _now_iso()
        self._state["processed_sessions"] = sorted(self._processed_sessions)
        self._state["processed_order_tokens"] = sorted(self._processed_order_tokens)
        self.state_path.write_text(
            json.dumps(self._state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------
    def _resolve_key(self, text: str | None) -> str | None:
        normalized = _normalize_text(text)
        if not normalized:
            return None
        for key, aliases in self.ALIASES.items():
            if any(alias in normalized for alias in aliases):
                return key
        if normalized in self._state.get("items", {}):
            return normalized
        return None

    def _ensure_item(self, key: str) -> InventoryItem:
        items = self._state.setdefault("items", {})
        if key not in items:
            items[key] = InventoryItem(
                key=key,
                label=key,
                count=0,
                threshold=3,
                reorder_qty=10,
                unit="块",
            ).to_dict()
        return InventoryItem.from_dict(items[key])

    def _write_item(self, item: InventoryItem) -> None:
        self._state.setdefault("items", {})[item.key] = item.to_dict()

    def _trim(self, key: str, limit: int = 50) -> None:
        entries = self._state.setdefault(key, [])
        if len(entries) > limit:
            del entries[:-limit]

    def _materialize_item(self, item: InventoryItem) -> dict[str, Any]:
        low_stock = item.count <= item.threshold
        order_url = self.build_order_url(
            item.key,
            item.reorder_qty,
            token=item.last_alert_token or None,
        )
        payload = item.to_dict()
        payload.update(
            {
                "status": "low_stock" if low_stock else "ok",
                "low_stock": low_stock,
                "order_url": order_url,
            }
        )
        return payload

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            items = [
                self._materialize_item(InventoryItem.from_dict(value))
                for key, value in sorted(self._state.get("items", {}).items(), key=lambda item: item[0])
            ]
            return deepcopy(
                {
                    "items": items,
                    "history": list(self._state.get("history", [])),
                    "alerts": list(self._state.get("alerts", [])),
                    "orders": list(self._state.get("orders", [])),
                    "updated_at": self._state.get("updated_at", _now_iso()),
                    "public_base_url": self.public_base_url,
                }
            )

    def build_order_url(self, sku: str, quantity: int | None = None, *, token: str | None = None) -> str:
        qty = int(quantity or self._ensure_item(sku).reorder_qty or 1)
        base = (
            f"{self.public_base_url}/api/inventory/order"
            f"?sku={quote(sku)}&quantity={qty}&source=feishu"
        )
        if token:
            base += f"&token={quote(token)}"
        return base

    def record_task_success(
        self,
        *,
        task: dict[str, Any],
        command: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Consume inventory for a successful grasp-like task."""

        with self._lock:
            if session_id and session_id in self._processed_sessions:
                return None

            source = task.get("source") or command
            sku = self._resolve_key(str(source) if source is not None else None)
            if not sku:
                if session_id:
                    self._processed_sessions.add(session_id)
                    self._save_state()
                return None

            item = self._ensure_item(sku)
            previous = item.count
            item.count = max(0, item.count - 1)
            item.last_updated_at = _now_iso()

            low_stock = item.count <= item.threshold
            alert_sent = False
            if low_stock and not item.alert_sent:
                item.alert_sent = True
                item.last_alert_at = _now_iso()
                item.last_alert_token = uuid.uuid4().hex
                alert_sent = True

            self._write_item(item)
            event = {
                "kind": "low_stock_alert" if alert_sent else "consume",
                "sku": item.key,
                "label": item.label,
                "unit": item.unit,
                "previous": previous,
                "remaining": item.count,
                "threshold": item.threshold,
                "reorder_qty": item.reorder_qty,
                "alert_sent": alert_sent,
                "order_pending": item.order_pending,
                "order_url": self.build_order_url(item.key, item.reorder_qty, token=item.last_alert_token or None),
                "order_token": item.last_alert_token,
                "source": source,
                "session_id": session_id,
                "command": command,
                "timestamp": _now_iso(),
            }
            self._state.setdefault("history", []).append(event)
            if alert_sent:
                self._state.setdefault("alerts", []).append(event)
            if session_id:
                self._processed_sessions.add(session_id)
            self._trim("history")
            self._trim("alerts")
            self._save_state()
            return event

    def record_order(
        self,
        *,
        sku: str,
        quantity: int,
        source: str = "feishu",
        session_id: str | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if token and token in self._processed_order_tokens:
                item = self._ensure_item(sku)
                return {
                    "status": "duplicate",
                    "duplicate": True,
                    "sku": item.key,
                    "label": item.label,
                    "quantity": int(quantity),
                    "source": source,
                    "session_id": session_id,
                    "token": token,
                    "timestamp": _now_iso(),
                }

            item = self._ensure_item(sku)
            item.order_pending = True
            item.last_order_at = _now_iso()
            self._write_item(item)
            if token:
                self._processed_order_tokens.add(token)
            order = {
                "sku": item.key,
                "label": item.label,
                "quantity": int(quantity),
                "source": source,
                "session_id": session_id,
                "token": token,
                "timestamp": _now_iso(),
            }
            self._state.setdefault("orders", []).append(order)
            self._trim("orders")
            self._save_state()
            with self.orders_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(order, ensure_ascii=False) + "\n")
            return order

    def replenish(self, *, sku: str, quantity: int) -> dict[str, Any]:
        with self._lock:
            item = self._ensure_item(sku)
            previous = item.count
            item.count += int(quantity)
            item.last_updated_at = _now_iso()
            if item.count > item.threshold:
                item.alert_sent = False
                item.order_pending = False
                item.last_alert_token = ""
            self._write_item(item)
            event = {
                "kind": "replenish",
                "sku": item.key,
                "label": item.label,
                "previous": previous,
                "remaining": item.count,
                "threshold": item.threshold,
                "timestamp": _now_iso(),
            }
            self._state.setdefault("history", []).append(event)
            self._trim("history")
            self._save_state()
            return event

    def set_item_count(self, *, sku: str, count: int) -> dict[str, Any]:
        with self._lock:
            item = self._ensure_item(sku)
            previous = item.count
            item.count = max(0, int(count))
            item.last_updated_at = _now_iso()
            if item.count > item.threshold:
                item.alert_sent = False
                item.order_pending = False
                item.last_alert_token = ""
            self._write_item(item)
            event = {
                "kind": "set",
                "sku": item.key,
                "label": item.label,
                "previous": previous,
                "remaining": item.count,
                "threshold": item.threshold,
                "timestamp": _now_iso(),
            }
            self._state.setdefault("history", []).append(event)
            self._trim("history")
            self._save_state()
            return event


_STORE: InventoryStore | None = None


def get_inventory_store() -> InventoryStore:
    global _STORE
    if _STORE is None:
        _STORE = InventoryStore()
    return _STORE
