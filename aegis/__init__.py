"""Governance layer for production AI agents in regulated industries."""
from aegis.approvals import ApprovalQueue, ApprovalRequest
from aegis.audit import AuditLog, AuditEntry
from aegis.gates import EvalCase, EvalGate, EvalSuite, GateReport
from aegis.packs import CompliancePack
from aegis.packs.sr117 import SR117_PACK
from aegis.policy import PolicyEngine, Policy, PolicyResult, STANDARD_POLICIES
from aegis.reports import generate

__all__ = [
    "ApprovalQueue", "ApprovalRequest",
    "AuditLog", "AuditEntry",
    "CompliancePack", "SR117_PACK",
    "EvalCase", "EvalGate", "EvalSuite", "GateReport",
    "PolicyEngine", "Policy", "PolicyResult", "STANDARD_POLICIES",
    "generate",
]
__version__ = "0.3.0"
