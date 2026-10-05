"""Policy engine: declare rules agents must obey, evaluate actions against them.

A policy is a named rule with a condition over the action's detail dict.
Verdicts: "allow", "deny", "escalate" (pause for human review).

Policies are plain data — version them in git, review them like code.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Policy:
    name: str
    description: str = ""
    # condition receives the action detail dict and returns True if the
    # policy is violated.
    condition: object = None
    verdict: str = "deny"  # deny | escalate


@dataclass
class PolicyResult:
    verdict: str  # allow | deny | escalate
    triggered: list[str] = field(default_factory=list)


class PolicyEngine:
    def __init__(self, policies: list[Policy] | None = None):
        self.policies: list[Policy] = list(policies or [])

    def add(self, policy: Policy) -> None:
        self.policies.append(policy)

    def evaluate(self, detail: dict) -> PolicyResult:
        triggered: list[str] = []
        verdict = "allow"
        for policy in self.policies:
            try:
                violated = bool(policy.condition(detail)) if policy.condition else False
            except Exception:
                violated = False
            if violated:
                triggered.append(policy.name)
                if policy.verdict == "deny":
                    verdict = "deny"
                elif verdict != "deny" and policy.verdict == "escalate":
                    verdict = "escalate"
        return PolicyResult(verdict=verdict, triggered=triggered)


# ---- Standard policies for regulated deployments ---------------------------

def no_pii_to_external_tools(detail: dict) -> bool:
    """Violated when PII fields are sent to a tool marked external."""
    if not detail.get("tool_external"):
        return False
    payload = str(detail.get("payload", ""))
    pii_markers = detail.get("pii_markers", [])
    return any(m in payload for m in pii_markers)


def financial_advice_needs_approval(detail: dict) -> bool:
    return (
        detail.get("action_type") == "financial_recommendation"
        and not detail.get("human_approved", False)
    )


def spend_cap(detail: dict) -> bool:
    return float(detail.get("amount_usd", 0)) > float(detail.get("spend_cap_usd", 1e12))


STANDARD_POLICIES = [
    Policy(
        name="no_pii_to_external_tools",
        description="Customer PII must never leave the boundary via external tools.",
        condition=no_pii_to_external_tools,
        verdict="deny",
    ),
    Policy(
        name="financial_advice_needs_approval",
        description="Financial recommendations require explicit human approval.",
        condition=financial_advice_needs_approval,
        verdict="escalate",
    ),
    Policy(
        name="spend_cap",
        description="Block autonomous actions above the per-session spend cap.",
        condition=spend_cap,
        verdict="deny",
    ),
]
