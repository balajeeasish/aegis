from aegis.approvals import ApprovalQueue
from aegis.audit import AuditLog


def _queue(tmp_path=None):
    import tempfile, os
    d = tempfile.mkdtemp() if tmp_path is None else str(tmp_path)
    log = AuditLog(os.path.join(d, "audit.jsonl"))
    return ApprovalQueue(log), log


def test_request_opens_pending():
    q, _ = _queue()
    req = q.request("advisor-agent", "recommendation",
                    {"payload": "move to fund X"},
                    triggered_policies=["financial_advice_needs_approval"])
    assert req.status == "pending"
    assert len(q.pending()) == 1


def test_approve_records_decision_and_audit():
    q, log = _queue()
    req = q.request("advisor-agent", "recommendation")
    out = q.approve(req.id, by="risk-officer", reason="client confirmed in writing")
    assert out.status == "approved"
    assert out.decided_by == "risk-officer"
    assert q.pending() == []
    actions = [e["action"] for e in log.entries()]
    assert "approval_requested" in actions
    assert "approval_approved" in actions


def test_decline_and_double_decide_rejected():
    q, _ = _queue()
    req = q.request("advisor-agent", "recommendation")
    q.decline(req.id, by="risk-officer", reason="too aggressive")
    assert req.status == "declined"
    try:
        q.approve(req.id, by="someone")
    except ValueError:
        pass
    else:
        raise AssertionError("double decision should fail")


def test_unknown_request_raises():
    q, _ = _queue()
    try:
        q.approve("nope", by="x")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown id should fail")


def test_expired_requests_swept():
    q, log = _queue()
    q.ttl_seconds = -1  # already expired
    req = q.request("advisor-agent", "recommendation")
    assert q.pending() == []  # sweep runs inside pending()
    assert req.status == "expired"
    assert any(e["action"] == "approval_expired" for e in log.entries())
