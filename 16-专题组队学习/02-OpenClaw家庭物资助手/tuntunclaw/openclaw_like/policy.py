"""Minimal policy gate for user commands."""

BLOCKLIST = [
    "self-harm",
    "suicide",
    "weapon",
    "bomb",
]


def check_user_command(command: str) -> tuple[bool, str]:
    lower = command.lower()
    for token in BLOCKLIST:
        if token in lower:
            return False, f"Blocked by policy token: {token}"
    return True, "ok"
