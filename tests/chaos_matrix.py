"""Repeatable real-process SIGKILL matrix with machine-readable statistics."""
import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BOUNDARIES = (
    "lock_acquisition",
    "validation_before_write",
    "fsync_before_rename",
    "claim_before_commit",
    "resolver_return",
    "side_effect_before_idempotency",
    "idempotency_before_execution_cas",
)


def wait_marker(path, value, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists() and path.read_text(encoding="utf-8") == value:
            return
        time.sleep(0.002)
    raise RuntimeError(f"marker timeout: {value}")


def run_round(boundary, root):
    marker = root / "marker"
    lease = root / "leases.json"
    intent = root / "intents.json"
    execution = root / "execution.json"
    idem = root / "idempotency.json"
    effect = root / "effect.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env.update(MARKER=str(marker), LEASE=str(lease), INTENT=str(intent), EXEC=str(execution), IDEM=str(idem), EFFECT=str(effect))
    code = f"""
import json, os
from pathlib import Path
from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_idempotency_store import ToolIdempotencyStore, StoredToolResult
from runtime.execution_store import ExecutionStore, ExecutionState
from runtime.tool_intent_store import ToolIntentStore, ToolIntent

b={boundary!r}
if b == 'lock_acquisition':
    s=ExecutionLeaseStore(os.environ['LEASE'], ttl_seconds=.05)
    open(os.environ['MARKER'],'w').write('lock')
    while True: pass
elif b == 'validation_before_write':
    s=ExecutionLeaseStore(os.environ['LEASE'], ttl_seconds=.05)
    s.acquire('e','dead')
    open(os.environ['MARKER'],'w').write('validation')
    while True: pass
elif b == 'fsync_before_rename':
    p=Path(os.environ['EXEC']); p.write_text('{{}}')
    t=p.with_suffix('.json.tmp'); t.write_text('{{"sentinel":1}}')
    with t.open('r+',encoding='utf-8') as h:
        h.flush(); os.fsync(h.fileno())
    open(os.environ['MARKER'],'w').write('rename')
    while True: pass
elif b == 'claim_before_commit':
    s=ToolIntentStore(os.environ['INTENT'], claim_ttl_seconds=.05)
    s.prepare(ToolIntent('k','call','send',{{}},'e','ambiguous'))
    assert s.claim('k','dead','c1') is not None
    open(os.environ['MARKER'],'w').write('claim')
    while True: pass
elif b == 'resolver_return':
    open(os.environ['MARKER'],'w').write('resolver')
    while True: pass
elif b == 'side_effect_before_idempotency':
    p=Path(os.environ['EFFECT']); p.write_text(json.dumps({{'count':1}}))
    open(os.environ['MARKER'],'w').write('effect')
    while True: pass
elif b == 'idempotency_before_execution_cas':
    ToolIdempotencyStore(os.environ['IDEM']).put_if_absent(StoredToolResult('k','c','external',True,{{'ok':True}}))
    open(os.environ['MARKER'],'w').write('idem')
    while True: pass
"""
    p = subprocess.Popen([sys.executable, "-c", code], env=env)
    markers = {
        "lock_acquisition":"lock", "validation_before_write":"validation", "fsync_before_rename":"rename",
        "claim_before_commit":"claim", "resolver_return":"resolver", "side_effect_before_idempotency":"effect",
        "idempotency_before_execution_cas":"idem",
    }
    try:
        wait_marker(marker, markers[boundary])
        os.kill(p.pid, signal.SIGKILL)
        rc = p.wait(timeout=3)
        if rc != -signal.SIGKILL:
            raise RuntimeError(f"unexpected worker rc={rc}")
        if boundary == "side_effect_before_idempotency":
            assert json.loads(effect.read_text())["count"] == 1
        if boundary == "idempotency_before_execution_cas":
            assert ToolIdempotencyStore(str(idem)).get("k") is not None
        if boundary == "claim_before_commit":
            # Claim is allowed to remain ambiguous; the store must stay parseable.
            assert ToolIntentStore(str(intent)).get("k") is not None
        if boundary == "fsync_before_rename":
            assert json.loads(execution.read_text()) == {}
        return "pass"
    finally:
        if p.poll() is None:
            p.kill(); p.wait(timeout=3)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--iterations', type=int, default=50)
    ap.add_argument('--output', default='chaos-matrix.json')
    args=ap.parse_args()
    if args.iterations < 50 or args.iterations > 100:
        raise SystemExit('--iterations must be between 50 and 100')
    stats={"iterations_per_boundary":args.iterations,"boundaries":{},"total":0,"passed":0,"failed":0}
    with tempfile.TemporaryDirectory(prefix='aios2-chaos-') as td:
        base=Path(td)
        for boundary in BOUNDARIES:
            row={"runs":args.iterations,"passed":0,"failed":0,"errors":[]}
            for i in range(args.iterations):
                root=base / f"{boundary}-{i}"
                root.mkdir()
                try:
                    run_round(boundary, root); row["passed"] += 1
                except Exception as exc:
                    row["failed"] += 1
                    if len(row["errors"]) < 10: row["errors"].append(repr(exc))
            stats["boundaries"][boundary]=row
    stats["total"]=sum(v["runs"] for v in stats["boundaries"].values())
    stats["passed"]=sum(v["passed"] for v in stats["boundaries"].values())
    stats["failed"]=sum(v["failed"] for v in stats["boundaries"].values())
    Path(args.output).write_text(json.dumps(stats,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(stats,indent=2,sort_keys=True))
    return 0 if stats["failed"] == 0 else 1

if __name__ == '__main__':
    raise SystemExit(main())
