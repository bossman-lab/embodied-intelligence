"""Shared workflow side-effects for successful robot actions."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from integrations import get_feishu_notifier, notify_robot_backend
from inventory import InventoryStore


@lru_cache(maxsize=1)
def get_inventory_store() -> InventoryStore:
    return InventoryStore()


def record_task_success_effects(
    *,
    task: dict[str, Any],
    command: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any] | None:
    """Record inventory consumption and fan out notifications."""

    store = get_inventory_store()
    event = store.record_task_success(task=task, command=command, session_id=session_id)

    webhook_payload = {
        "kind": "task_success",
        "task": task,
        "command": command,
        "session_id": session_id,
        "inventory_event": event,
        "timestamp": event.get("timestamp") if event else None,
    }
    notify_robot_backend(webhook_payload)

    if event and event.get("alert_sent"):
        try:
            get_feishu_notifier().send_low_stock_alert(event)
        except Exception:
            # Notifications should never block the robot workflow.
            pass

    return event
