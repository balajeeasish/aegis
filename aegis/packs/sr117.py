"""SR 11-7 compliance pack: Federal Reserve Supervisory Guidance on Model
Risk Management, mapped to AI agent governance.

SR 11-7 expects banks to run a model risk management framework covering:
model inventory and risk tiering, independent validation, ongoing monitoring
and outcomes analysis, change control with documentation, and restricting
models to their approved uses. This pack turns those expectations into
enforceable agent policies. Each policy cites the SR 11-7 element it serves.

This is a practitioner's mapping, not legal advice.
"""
from __future__ import annotations

from aegis.packs import CompliancePack
from aegis.policy import Policy


def unregistered_model(detail: dict) -> bool:
    """Deny: the agent's model is not in the approved model inventory."""
    return detail.get("model_id") not in (detail.get("registered_models") or [])


def high_risk_without_validation(detail: dict) -> bool:
    """Escalate: high-risk agent change lacking independent validation."""
    return (
        detail.get("risk_tier") == "high"
        and not detail.get("independently_validated", False)
    )


def deployment_without_eval_evidence(detail: dict) -> bool:
    """Deny: deploying an agent version with no passing eval gate on record."""
    return (
        detail.get("action_type") == "agent_deployment"
        and detail.get("eval_gate_verdict") != "promote"
    )


def undocumented_material_change(detail: dict) -> bool:
    """Escalate: material change with no change-control record attached."""
    return bool(detail.get("material_change")) and not detail.get("change_record_id")


def unapproved_use(detail: dict) -> bool:
    """Deny: agent operating outside its approved use cases."""
    use_case = detail.get("use_case")
    approved = detail.get("approved_use_cases") or []
    return bool(use_case) and use_case not in approved


SR117_PACK = CompliancePack(
    name="sr117",
    framework="OCC/Federal Reserve SR 11-7 — Supervisory Guidance on Model Risk Management",
    version="1.0",
    description=(
        "Maps SR 11-7 model-risk expectations to enforceable AI agent policies: "
        "inventory, independent validation, ongoing monitoring, change control, "
        "and approved-use restrictions."
    ),
    references={
        "sr117_model_inventory": "SR 11-7 — Model inventory: comprehensive set of models with risk tiering",
        "sr117_independent_validation": "SR 11-7 — Model validation: independent, qualified validation before use",
        "sr117_eval_gate_evidence": "SR 11-7 — Ongoing monitoring and outcomes analysis",
        "sr117_change_documentation": "SR 11-7 — Change control and documentation standards",
        "sr117_approved_use": "SR 11-7 — Model use: restrict to approved purposes and markets",
    },
    policies=[
        Policy(
            name="sr117_model_inventory",
            description="Only models registered in the approved inventory may act.",
            condition=unregistered_model,
            verdict="deny",
        ),
        Policy(
            name="sr117_independent_validation",
            description="High-risk agent changes require independent validation first.",
            condition=high_risk_without_validation,
            verdict="escalate",
        ),
        Policy(
            name="sr117_eval_gate_evidence",
            description="Agent deployments require a passing eval gate on record.",
            condition=deployment_without_eval_evidence,
            verdict="deny",
        ),
        Policy(
            name="sr117_change_documentation",
            description="Material changes require a change-control record.",
            condition=undocumented_material_change,
            verdict="escalate",
        ),
        Policy(
            name="sr117_approved_use",
            description="Agents may only operate within approved use cases.",
            condition=unapproved_use,
            verdict="deny",
        ),
    ],
)
