"""Immutable, tamper-evident audit trail for agent actions.

Every entry is hash-chained to the previous one: tampering with any
historical entry breaks the chain and is detectable via verify().
Storage is JSONL — boring, portable, and human-readable.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AuditEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts: float = field(default_factory=time.time)
    actor: str = ""            # which agent / component acted
    action: str = ""           # what it did, e.g. "tool_call", "message_send"
    detail: dict = field(default_factory=dict)
    policy_verdict: str = ""   # allow / deny / escalate
    prev_hash: str = ""
    hash: str = ""

    def canonical(self) -> str:
        d = asdict(self)
        d.pop("hash")
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    def seal(self, prev_hash: str) -> "AuditEntry":
        self.prev_hash = prev_hash
        self.hash = hashlib.sha256(
            (prev_hash + self.canonical()).encode()
        ).hexdigest()
        return self


class AuditLog:
    """Append-only audit log backed by a JSONL file."""

    GENESIS = "GENESIS"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _last_hash(self) -> str:
        last = self.GENESIS
        if self.path.stat().st_size:
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last = json.loads(line)["hash"]
        return last

    def record(self, actor: str, action: str, detail: dict | None = None,
               policy_verdict: str = "") -> AuditEntry:
        entry = AuditEntry(
            actor=actor, action=action,
            detail=detail or {}, policy_verdict=policy_verdict,
        ).seal(self._last_hash())
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def entries(self) -> list[dict]:
        out = []
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def verify(self) -> tuple[bool, str]:
        """Walk the chain; return (ok, message)."""
        prev = self.GENESIS
        for i, e in enumerate(self.entries()):
            if e["prev_hash"] != prev:
                return False, f"chain broken at entry {i} ({e['id']})"
            recomputed = hashlib.sha256(
                (e["prev_hash"] + json.dumps(
                    {k: v for k, v in e.items() if k != "hash"},
                    sort_keys=True, separators=(",", ":"),
                )).encode()
            ).hexdigest()
            if recomputed != e["hash"]:
                return False, f"tampered entry {i} ({e['id']})"
            prev = e["hash"]
        return True, f"chain intact ({len(self.entries())} entries)"
