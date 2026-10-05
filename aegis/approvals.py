"""Human-in-the-loop approvals: escalated actions pause for human review.

When the policy engine returns "escalate", the action does not run. Instead
an ApprovalRequest is opened in the queue. A human approves or declines with
their identity and a reason, and every step is written to the audit trail —
including overrides, which is what regulators actually ask about.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from aegis.audit import AuditLog


@dataclass
class ApprovalRequest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts: float = field(default_factory=time.time)
    actor: str = ""
    action: str = ""
    detail: dict = field(default_factory=dict)
    triggered_policies: list[str] = field(default_factory=list)
    status: str = "pending"          # pending | approved | declined | expired
    decided_by: str = ""
    decided_at: float = 0.0
    reason: str = ""
    expires_at: float = 0.0


class ApprovalQueue:
    """In-memory queue; the audit log is the durable record."""

    def __init__(self, audit: AuditLog | None = None, ttl_seconds: float = 3600):
        self._requests: dict[str, ApprovalRequest] = {}
        self.audit = audit
        self.ttl_seconds = ttl_seconds

    def request(self, actor: str, action: str, detail: dict | None = None,
                triggered_policies: list[str] | None = None) -> ApprovalRequest:
        req = ApprovalRequest(
            actor=actor, action=action, detail=detail or {},
            triggered_policies=list(triggered_policies or []),
            expires_at=time.time() + self.ttl_seconds,
        )
        self._requests[req.id] = req
        if self.audit:
            self.audit.record(actor, "approval_requested",
                              {"request_id": req.id, "action": action,
                               "policies": req.triggered_policies},
                              policy_verdict="escalate")
        return req

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def pending(self) -> list[ApprovalRequest]:
        self.sweep_expired()
        return [r for r in self._requests.values() if r.status == "pending"]

    def _decide(self, request_id: str, by: str, reason: str,
                status: str) -> ApprovalRequest:
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"unknown approval request: {request_id}")
        if req.status != "pending":
            raise ValueError(f"request {request_id} already {req.status}")
        req.status = status
        req.decided_by = by
        req.decided_at = time.time()
        req.reason = reason
        if self.audit:
            self.audit.record(req.actor, f"approval_{status}",
                              {"request_id": req.id, "action": req.action,
                               "decided_by": by, "reason": reason},
                              policy_verdict="escalate")
        return req

    def approve(self, request_id: str, by: str, reason: str = "") -> ApprovalRequest:
        return self._decide(request_id, by, reason, "approved")

    def decline(self, request_id: str, by: str, reason: str = "") -> ApprovalRequest:
        return self._decide(request_id, by, reason, "declined")

    def sweep_expired(self) -> list[ApprovalRequest]:
        now = time.time()
        expired = [r for r in self._requests.values()
                   if r.status == "pending" and r.expires_at and r.expires_at < now]
        for req in expired:
            req.status = "expired"
            if self.audit:
                self.audit.record(req.actor, "approval_expired",
                                  {"request_id": req.id, "action": req.action},
                                  policy_verdict="escalate")
        return expired
