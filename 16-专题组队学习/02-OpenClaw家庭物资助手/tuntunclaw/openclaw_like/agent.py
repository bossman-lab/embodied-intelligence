"""OpenClaw-like agent loop (CLI)."""

from openclaw_like.session import Session
from openclaw_like.memory import MemoryStore
from openclaw_like.policy import check_user_command
from openclaw_like.tool_router import ToolRouter


class IronClawLikeAgent:
    def __init__(self) -> None:
        self.session = Session()
        self.memory = MemoryStore()
        self.tools = ToolRouter()

    def run(self) -> None:
        print("[agent] OpenClaw-like loop started. Type 'exit' to stop.")
        try:
            while True:
                command = input("claw> ").strip()
                if not command:
                    continue
                if command.lower() in {"exit", "quit"}:
                    break

                turn = self.session.next_turn()
                allowed, reason = check_user_command(command)
                if not allowed:
                    print(f"[policy] {reason}")
                    self.memory.append(
                        {
                            "session_id": self.session.session_id,
                            "turn": turn,
                            "role": "policy",
                            "status": "blocked",
                            "command": command,
                            "reason": reason,
                        }
                    )
                    continue

                print("[router] grasp_once")
                result = self.tools.grasp_once(command)
                print(f"[done] {result}")
                self.memory.append(
                    {
                        "session_id": self.session.session_id,
                        "turn": turn,
                        "role": "agent",
                        "status": "ok",
                        "command": command,
                        "result": result,
                    }
                )
        finally:
            self.tools.close()
            print("[agent] closed")
