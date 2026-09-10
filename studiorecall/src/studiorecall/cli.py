from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .core import RecallUnavailable, StaleRevision, evaluate_release, hard_forget, open_memory, record_gate, utc_now


def commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "uncommitted"


def context() -> dict[str, str | int]:
    return {"timestamp_utc": utc_now(), "pid": os.getpid(), "commit": commit_hash()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="studiorecall", description="Sibyl-backed release continuity for AI-agent studios")
    parser.add_argument("--db", default=".studiorecall/memory.db", help="Sibyl Memory SQLite path")
    parser.add_argument("--tenant", default="00000000-0000-0000-0000-000000000001")
    sub = parser.add_subparsers(dest="command", required=True)

    seed = sub.add_parser("remember", help="Remember a release gate")
    seed.add_argument("--project", required=True)
    seed.add_argument("--revision", type=int, required=True)
    seed.add_argument("--status", choices=["BLOCKED", "READY"], required=True)
    seed.add_argument("--rule", required=True)
    seed.add_argument("--evidence", required=True)

    check = sub.add_parser("check", help="Recall a prior gate in a fresh process")
    check.add_argument("--project", required=True)

    forget = sub.add_parser("forget", help="Hard-delete the load-bearing release memory")
    forget.add_argument("--project", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    memory = open_memory(args.db, tenant_id=args.tenant)
    meta = context()

    try:
        if args.command == "remember":
            saved = record_gate(memory, project=args.project, revision=args.revision, status=args.status, rule=args.rule, evidence=args.evidence)
            print(json.dumps({"session": meta, "remembered": saved["body"]}, indent=2))
            return 0

        if args.command == "check":
            result = evaluate_release(memory, project=args.project)
            payload = {
                "session": meta,
                "fresh_session_recall": True,
                "project": result.project,
                "remembered_revision": result.revision,
                "release_decision": result.decision,
                "rule": result.rule,
                "evidence": result.evidence,
                "recorded_at": result.recorded_at,
            }
            print(json.dumps(payload, indent=2))
            return 0

        if args.command == "forget":
            hard_forget(memory, project=args.project)
            print(json.dumps({"session": meta, "hard_deleted": args.project}, indent=2))
            return 0

    except (RecallUnavailable, StaleRevision, ValueError) as exc:
        print(json.dumps({"session": meta, "error": exc.__class__.__name__, "message": str(exc)}, indent=2), file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
