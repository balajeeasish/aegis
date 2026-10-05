import os
import tempfile

import pytest

from aegis.audit import AuditLog
from aegis.policy import PolicyEngine, Policy, STANDARD_POLICIES


@pytest.fixture
def log():
    d = tempfile.mkdtemp()
    return AuditLog(os.path.join(d, "audit.jsonl"))


def test_policy_allows_clean_action():
    engine = PolicyEngine(STANDARD_POLICIES)
    r = engine.evaluate({"tool_external": False, "payload": "hello"})
    assert r.verdict == "allow" and r.triggered == []


def test_policy_denies_pii_exfiltration():
    engine = PolicyEngine(STANDARD_POLICIES)
    r = engine.evaluate({
        "tool_external": True,
        "payload": "send ssn: 123-45-6789",
        "pii_markers": ["ssn:"],
    })
    assert r.verdict == "deny"
    assert "no_pii_to_external_tools" in r.triggered


def test_policy_escalates_unapproved_advice():
    engine = PolicyEngine(STANDARD_POLICIES)
    r = engine.evaluate({
        "action_type": "financial_recommendation",
        "human_approved": False,
    })
    assert r.verdict == "escalate"


def test_deny_beats_escalate():
    engine = PolicyEngine([
        Policy("e", condition=lambda d: True, verdict="escalate"),
        Policy("d", condition=lambda d: True, verdict="deny"),
    ])
    assert engine.evaluate({}).verdict == "deny"


def test_audit_chain_verifies(log):
    log.record("a", "tool_call", {"x": 1}, "allow")
    log.record("a", "tool_call", {"x": 2}, "deny")
    ok, msg = log.verify()
    assert ok, msg
    assert len(log.entries()) == 2


def test_audit_detects_tampering(log):
    log.record("a", "tool_call", {"x": 1}, "allow")
    # tamper with the file directly
    entries = log.entries()
    entries[0]["detail"] = {"x": 999}
    import json
    with open(log.path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    ok, msg = log.verify()
    assert not ok
    assert "tampered" in msg
