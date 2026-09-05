from typing import Any

from .errors import ZohoError


def message_id(message: dict[str, Any]) -> str:
    value = message.get("messageId")
    if value is None:
        raise ZohoError(f"Zoho message has no messageId: {message}")
    return str(value)


def zoho_thread_id(message: dict[str, Any]) -> str:
    return str(message.get("threadId") or message_id(message))


def received_time(message: dict[str, Any]) -> int:
    try:
        return int(message.get("receivedTime", 0))
    except (TypeError, ValueError):
        return 0
