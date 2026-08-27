# AIOS2 Roadmap

## P0 — make execution authoritative

- [ ] Add monotonic execution version and compare-and-set lifecycle mutations.
- [ ] Pass fencing generation through `ExecutionCommitCoordinator` into persistence.
- [ ] Reject stale fencing generations atomically at the persistence boundary.
- [ ] Remove/privatize runtime lifecycle mutation paths that bypass the coordinator.
- [ ] Add subprocess crash/fault-injection tests for every journal/store/audit ordering window.
- [ ] Add deterministic concurrency tests for two workers racing the same execution.

## P1 — complete the operating-system substrate

- [ ] Capability/policy engine shared by tools, operators, recovery and agents.
- [ ] Stable Agent identity, lifecycle and capability model.
- [ ] LLM provider/model abstraction.
- [ ] Durable Memory runtime: working, episodic, semantic and procedural memory.
- [ ] Cognition runtime: planner, evaluator, reflector and learner.
- [ ] Event publication derived from committed state, with delivery/retry semantics.
- [ ] Public execution/agent/tool API over canonical execution identity.

## P2 — distributed production runtime

- [ ] Distributed execution repository with CAS/versioning.
- [ ] Durable distributed journal/log.
- [ ] Distributed leases with fencing.
- [ ] Multi-machine recovery and takeover tests.
- [ ] Observability: traces, metrics, structured audit and execution correlation.

## P3 — autonomous multi-agent system

- [ ] Agent-to-agent communication.
- [ ] Delegation and shared goals.
- [ ] Swarm orchestration.
- [ ] Experience → memory → evaluation → learning pipeline.
- [ ] Strategy optimization and bounded self-improvement.

## Completion criterion

AIOS2 is an autonomous-agent operating system when a single canonical execution can survive crashes, concurrent workers and restart; safely invoke capabilities; preserve experience; reason/replan; coordinate agents; and improve future behavior without creating parallel execution state authorities.
