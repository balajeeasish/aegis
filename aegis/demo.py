"""Demo: an agent action flows through the policy engine into the audit trail."""
from aegis.audit import AuditLog
from aegis.policy import PolicyEngine, STANDARD_POLICIES


def main() -> None:
    log = AuditLog("/tmp/aegis-demo.jsonl")
    engine = PolicyEngine(STANDARD_POLICIES)

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
        entry = log.record(actor, action, detail, result.verdict)
        print(f"[{result.verdict.upper():8}] {actor} {action} "
              f"(policies: {result.triggered or 'none'}) -> {entry.id}")

    ok, msg = log.verify()
    print("audit:", msg)


if __name__ == "__main__":
    main()
