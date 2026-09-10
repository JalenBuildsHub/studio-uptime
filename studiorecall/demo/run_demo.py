from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "artifacts" / "demo.db"
PROJECT = "nymrel-release"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(label: str, args: list[str], expected: int = 0) -> str:
    print(f"\n{'=' * 74}\n{label}\nUTC {now()}\n{'=' * 74}")
    cmd = [sys.executable, "-m", "studiorecall.cli", "--db", str(DB), *args]
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    print(output)
    print(f"exit={result.returncode}")
    if result.returncode != expected:
        raise SystemExit(f"unexpected exit code: expected {expected}, got {result.returncode}")
    return output


def main() -> int:
    for suffix in ("", "-shm", "-wal"):
        p = Path(str(DB) + suffix)
        if p.exists():
            p.unlink()

    print("NYMREL STUDIORECALL — SIBYL MEMORY LOAD-BEARING DEMO")
    print(f"driver_pid={os.getpid()} utc={now()}")
    print("Scenario: a new agent session must inherit an earlier release gate before giving release advice.")

    run(
        "SESSION A — write authoritative release gate to Sibyl Memory",
        ["remember", "--project", PROJECT, "--revision", "2", "--status", "BLOCKED", "--rule", "Do not deploy until independent exact-SHA review passes.", "--evidence", "review receipt absent"],
    )
    run("SESSION B — FRESH OS PROCESS recalls prior state", ["check", "--project", PROJECT])
    run(
        "CONFLICT TEST — stale revision 1 cannot overwrite remembered revision 2",
        ["remember", "--project", PROJECT, "--revision", "1", "--status", "READY", "--rule", "Old session says ship.", "--evidence", "stale evidence"],
        expected=2,
    )
    run("DELETION TEST — hard-delete the Sibyl entity", ["forget", "--project", PROJECT])
    run("SESSION C — FRESH OS PROCESS after deletion: continuity breaks", ["check", "--project", PROJECT], expected=2)
    print("\nPASS: Sibyl Memory is on StudioRecall's critical path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
