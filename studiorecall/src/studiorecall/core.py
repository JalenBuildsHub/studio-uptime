from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient

CATEGORY = "release-gate"
DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


class RecallUnavailable(RuntimeError):
    """Raised when the release decision cannot be reconstructed from Sibyl Memory."""


class StaleRevision(RuntimeError):
    """Raised when an older decision tries to overwrite a newer remembered decision."""


@dataclass(frozen=True)
class ReleaseDecision:
    project: str
    decision: str
    revision: int
    rule: str
    evidence: str
    recorded_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def open_memory(path: str | Path, *, tenant_id: str = DEFAULT_TENANT) -> MemoryClient:
    return MemoryClient.local(str(Path(path)), tenant_id=tenant_id)


def _get_entity(memory: MemoryClient, project: str) -> dict[str, Any] | None:
    try:
        return memory.get_entity(CATEGORY, project)
    except Exception as exc:  # Sibyl exposes NotFoundError from an internal module.
        if exc.__class__.__name__ == "NotFoundError":
            return None
        raise


def record_gate(
    memory: MemoryClient,
    *,
    project: str,
    revision: int,
    status: str,
    rule: str,
    evidence: str,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    status = status.upper()
    if status not in {"BLOCKED", "READY"}:
        raise ValueError("status must be BLOCKED or READY")

    current = _get_entity(memory, project)
    if current is not None:
        current_revision = int(current["body"]["revision"])
        if revision <= current_revision:
            raise StaleRevision(
                f"revision {revision} cannot overwrite remembered revision {current_revision}"
            )

    body = {
        "project": project,
        "revision": revision,
        "status": status,
        "rule": rule,
        "evidence": evidence,
        "recorded_at": recorded_at or utc_now(),
    }
    saved = memory.set_entity(CATEGORY, project, body, status=status.lower())
    memory.write_event(
        evaluated=[f"release gate {project} r{revision}"],
        acted=[f"remembered {status}: {rule}"],
        forward=[f"fresh sessions must recall {CATEGORY}/{project} before release advice"],
    )
    return saved


def recall_gate(memory: MemoryClient, *, project: str) -> ReleaseDecision:
    entity = _get_entity(memory, project)
    if entity is None:
        raise RecallUnavailable(
            f"Sibyl Memory has no {CATEGORY}/{project}; release continuity is unavailable"
        )
    body = entity["body"]
    return ReleaseDecision(
        project=project,
        decision=body["status"],
        revision=int(body["revision"]),
        rule=body["rule"],
        evidence=body["evidence"],
        recorded_at=body["recorded_at"],
    )


def evaluate_release(memory: MemoryClient, *, project: str) -> ReleaseDecision:
    remembered = recall_gate(memory, project=project)
    if remembered.decision not in {"BLOCKED", "READY"}:
        raise RecallUnavailable(f"remembered release state is not actionable: {remembered.decision}")
    return remembered


def hard_forget(memory: MemoryClient, *, project: str) -> None:
    # Permanent deletion is deliberate here: it is the hackathon load-bearing test.
    memory.delete_entity(CATEGORY, project)
    memory.write_event(acted=[f"hard-deleted {CATEGORY}/{project} for deletion test"])
