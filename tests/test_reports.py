import os
import tempfile

from aegis.approvals import ApprovalQueue
from aegis.audit import AuditLog
from aegis.gates import EvalCase, EvalGate, EvalSuite
from aegis.policy import PolicyEngine, STANDARD_POLICIES
from aegis.reports import generate


def _scenario():
    d = tempfile.mkdtemp()
    log = AuditLog(os.path.join(d, "audit.jsonl"))
    engine = PolicyEngine(STANDARD_POLICIES)
    queue = ApprovalQueue(log, ttl_seconds=3600)

    # one denied action
    detail = {"tool": "webhook", "tool_external": True,
              "payload": "notify ssn: 1", "pii_markers": ["ssn:"]}
    r = engine.evaluate(detail)
    log.record("support-agent", "tool_call",
               {**detail, "triggered_policies": r.triggered}, r.verdict)

    # one escalated action, approved by a human
    detail2 = {"action_type": "financial_recommendation", "human_approved": False}
    r2 = engine.evaluate(detail2)
    log.record("advisor-agent", "recommendation", detail2, r2.verdict)
    req = queue.request("advisor-agent", "recommendation", detail2, r2.triggered)
    queue.approve(req.id, by="risk-officer", reason="client confirmed")

    suite = EvalSuite("release", [EvalCase("a", lambda: True)])
    gate = EvalGate(suite, threshold=0.95).evaluate()
    return log, [gate]


def test_report_renders_all_sections():
    log, gates = _scenario()
    md = generate(log, gates, title="Q4 Agent Review")
    for section in ("# Q4 Agent Review", "## Verdict summary",
                    "## Policy triggers", "## Human approvals and overrides",
                    "## Eval gate evidence", "Chain integrity: INTACT"):
        assert section in md, section
    assert "no_pii_to_external_tools" in md
    assert "risk-officer" in md
    assert "PROMOTE" in md


def test_report_on_empty_log():
    d = tempfile.mkdtemp()
    md = generate(AuditLog(os.path.join(d, "audit.jsonl")))
    assert "Chain integrity: INTACT" in md
    assert "No approval decisions recorded" in md
