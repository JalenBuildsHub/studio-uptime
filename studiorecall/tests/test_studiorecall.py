from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from studiorecall.core import RecallUnavailable, StaleRevision, evaluate_release, hard_forget, open_memory, record_gate


def test_fresh_client_recalls_prior_release_gate(tmp_path: Path) -> None:
    db = tmp_path / "memory.db"
    first = open_memory(db)
    record_gate(first, project="nymrel-release", revision=1, status="BLOCKED", rule="Do not deploy until independent review passes.", evidence="review receipt absent")

    fresh_process_equivalent = open_memory(db)
    recalled = evaluate_release(fresh_process_equivalent, project="nymrel-release")
    assert recalled.decision == "BLOCKED"
    assert recalled.revision == 1
    assert "independent review" in recalled.rule


def test_deletion_breaks_core_continuity(tmp_path: Path) -> None:
    db = tmp_path / "memory.db"
    memory = open_memory(db)
    record_gate(memory, project="critical-path", revision=1, status="BLOCKED", rule="Release requires exact-SHA review evidence.", evidence="missing")
    hard_forget(memory, project="critical-path")

    with pytest.raises(RecallUnavailable):
        evaluate_release(open_memory(db), project="critical-path")


def test_stale_revision_cannot_overwrite_newer_decision(tmp_path: Path) -> None:
    memory = open_memory(tmp_path / "memory.db")
    record_gate(memory, project="alpha", revision=2, status="READY", rule="Gate passed.", evidence="receipt-2")
    with pytest.raises(StaleRevision):
        record_gate(memory, project="alpha", revision=1, status="BLOCKED", rule="Old state.", evidence="receipt-1")
    assert evaluate_release(memory, project="alpha").revision == 2


def test_tenant_isolation(tmp_path: Path) -> None:
    db = tmp_path / "memory.db"
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    a = open_memory(db, tenant_id=tenant_a)
    record_gate(a, project="same-name", revision=1, status="READY", rule="A is ready.", evidence="a")

    with pytest.raises(RecallUnavailable):
        evaluate_release(open_memory(db, tenant_id=tenant_b), project="same-name")
