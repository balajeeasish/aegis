"""Demo: the full Aegis loop — policy, audit, human approval, eval gate, report."""
from aegis.approvals import ApprovalQueue
from aegis.audit import AuditLog
from aegis.gates import EvalCase, EvalGate, EvalSuite
from aegis.policy import PolicyEngine, STANDARD_POLICIES
from aegis.reports import generate


def main() -> None:
    log = AuditLog("/tmp/aegis-demo.jsonl")
    engine = PolicyEngine(STANDARD_POLICIES)
    queue = ApprovalQueue(log)

    actions = [
        ("support-agent", "tool_call", {
            "tool": "crm_lookup", "tool_external": False,
            "payload": "lookup customer 123", "pii_markers": ["ssn:"],
        }),
        ("support-agent", "tool_call", {
            "tool": "webhook", "tool_external": True,
            "payload": "notify ssn: 123-45-6789", "pii_markers": ["ssn:"],
        }),
        ("advisor-agent", "recommendation", {
            "action_type": "financial_recommendation",
            "payload": "move to fund X", "human_approved": False,
        }),
    ]

    for actor, action, detail in actions:
        result = engine.evaluate(detail)
        entry = log.record(actor, action,
                           {**detail, "triggered_policies": result.triggered},
                           result.verdict)
        print(f"[{result.verdict.upper():8}] {actor} {action} "
              f"(policies: {result.triggered or 'none'}) -> {entry.id}")
        if result.verdict == "escalate":
            req = queue.request(actor, action, detail, result.triggered)
            print(f"           approval requested -> {req.id} "
                  f"(pending review by a human)")
            queue.approve(req.id, by="demo-reviewer",
                          reason="client confirmed in writing")
            print(f"           approved by demo-reviewer")

    suite = EvalSuite("release-smoke", [
        EvalCase("no-pii-leak", lambda: True),
        EvalCase("spend-cap-honored", lambda: True),
    ])
    gate = EvalGate(suite, threshold=0.95).evaluate()
    print(f"eval gate: {gate.suite} {gate.passed}/{gate.total} "
          f"-> {gate.verdict.upper()}")

    ok, msg = log.verify()
    print("audit:", msg)

    report = generate(log, [gate], title="Aegis Demo Compliance Report")
    with open("/tmp/aegis-demo-report.md", "w") as f:
        f.write(report)
    print("report: /tmp/aegis-demo-report.md")


if __name__ == "__main__":
    main()
