"""Append-only, compact JSON audit trail for Campus Customs agent activity."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"


class AuditTrail:
    """Persist agent events without deleting or replacing previous records."""

    def __init__(self, path: Path = AUDIT_PATH) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def record(
        self,
        *,
        agent: str,
        action: str,
        ticket_id: int | None = None,
        tool: str | None = None,
        result: Any = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "action": action,
        }
        if ticket_id is not None:
            event["ticket_id"] = ticket_id
        if tool:
            event["tool"] = tool
        if result is not None:
            event["result"] = _compact_result(result)

        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                content = self.path.read_text(encoding="utf-8").strip()
                records = json.loads(content) if content else []
                if not isinstance(records, list):
                    raise ValueError("audit trail must contain a JSON list")
            else:
                records = []
            records.append(event)
            self.path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
        return event


def _compact_result(result: Any) -> Any:
    """Keep audit evidence useful while avoiding large transcript copies."""
    if isinstance(result, str):
        return result if len(result) <= 500 else result[:497] + "..."
    if isinstance(result, (dict, list, int, float, bool)) or result is None:
        return result
    return str(result)


def audit_tool_call(
    audit: AuditTrail,
    *,
    agent: str,
    tool: str,
    ticket_id: int | None,
    result: Any,
) -> dict[str, Any]:
    """Record a completed MCP or peer-tool call in the common event format."""
    return audit.record(
        agent=agent,
        action="tool_call_completed",
        ticket_id=ticket_id,
        tool=tool,
        result=result,
    )
