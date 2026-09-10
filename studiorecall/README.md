# Nymrel StudioRecall

**Release continuity for agentic software studios, with Sibyl Memory on the critical path.**

StudioRecall remembers the release decision that a previous agent session made—what is blocked, what evidence is missing, and which revision is authoritative—then makes a fresh process recover that exact state before it can give release advice.

The target user is a multi-agent engineering studio where new sessions routinely inherit work from other agents. The failure mode is expensive: a fresh agent sees a green build but misses yesterday's release gate, stale decision, or required review and acts on incomplete context.

## Why Sibyl Memory is load-bearing

StudioRecall does **not** have a fallback release-state store. The authoritative release gate is a Sibyl Memory entity. A fresh process must call Sibyl to recover it.

Critical path:

1. `record_gate()` writes `release-gate/<project>` with `MemoryClient.set_entity(...)` and journals the transition with `write_event(...)` in `src/studiorecall/core.py`.
2. A later process calls `evaluate_release()` -> `recall_gate()` -> `MemoryClient.get_entity(...)`.
3. If the entity is absent, StudioRecall raises `RecallUnavailable` and cannot reconstruct the release decision.
4. `hard_forget()` uses Sibyl's permanent `delete_entity(...)`. The next fresh recall fails. That is the deletion test, not a simulated flag.

Remove the Sibyl calls and the product loses the capability it claims: cross-session release continuity.

## The product

A release gate contains:

- project identity
- monotonic revision
- `BLOCKED` or `READY` state
- the governing rule
- the evidence that supports the state
- the UTC time it was recorded

StudioRecall rejects an older revision that tries to overwrite a newer remembered decision. The same SQLite substrate can isolate different agent/studio identities with Sibyl tenant IDs.

## Quickstart

Python 3.10+ is required.

```bash
python -m venv .venv
# activate the environment, then:
pip install -e ".[dev]"
```

Remember a release gate in session A:

```bash
studiorecall --db artifacts/demo.db remember \
  --project nymrel-release \
  --revision 1 \
  --status BLOCKED \
  --rule "Do not deploy until independent review passes." \
  --evidence "review receipt absent"
```

Start a new process/session B and recall it:

```bash
studiorecall --db artifacts/demo.db check --project nymrel-release
```

The output includes the new process ID, current UTC timestamp, Git commit hash, the remembered revision, and the release decision.

Now run the load-bearing deletion test:

```bash
studiorecall --db artifacts/demo.db forget --project nymrel-release
studiorecall --db artifacts/demo.db check --project nymrel-release
```

The second command exits nonzero with `RecallUnavailable`. There is no local JSON or application fallback from which to rebuild the decision.

## Demo

The repository includes a continuous 2–5 minute demo at `demo/studiorecall-demo.mp4` plus the exact deterministic scenario in `demo/run_demo.py`.

The demo shows:

1. the problem and user;
2. session A writing a real Sibyl Memory release gate;
3. session B starting as a fresh OS process and recalling the prior state, with UTC timestamp, PID, and commit hash on screen;
4. a stale revision being rejected;
5. Sibyl hard deletion followed by the same fresh-process check failing.

## Tests

```bash
pytest
```

The suite covers:

- fresh-client persistence across sessions;
- deletion breaking the core continuity function;
- stale-revision protection;
- tenant isolation.

## Partner stacks

None claimed. This submission intentionally optimizes the mandatory memory path instead of adding an unused partner integration. Sibyl Memory is the only external stack used by the product and is exercised directly in the core path and demo.

## How memory made this possible

Release continuity is not ordinary retrieval. A studio needs one durable current truth per project, chronological evidence about how it changed, isolation between agent identities, and a deterministic failure when that truth disappears. Sibyl's WARM entity model provides the authoritative project gate, its journal records transitions, and its tenant boundary prevents one studio identity from inheriting another's gate. StudioRecall's release advice therefore depends on memory state created by an earlier session rather than re-deriving or hallucinating it from the current prompt.

## Prior Work declaration

The StudioRecall concept and hackathon planning packet existed before implementation. As of August 31, 2026, the packet explicitly recorded implementation as not started. All source code, tests, README content, and demo assets in this repository were created during the September 1–10, 2026 build window. No pre-existing StudioRecall source code was incorporated. The only third-party application dependency is the publicly released `sibyl-memory-client` package, used through its documented SDK.

## Repository map

```text
src/studiorecall/core.py   Sibyl-backed critical path
src/studiorecall/cli.py    CLI and fresh-session metadata
tests/                     deletion, persistence, stale-state, isolation tests
demo/run_demo.py           deterministic two-session demo driver
demo/studiorecall-demo.mp4 public demo asset
```

## License

MIT. See `LICENSE`.
