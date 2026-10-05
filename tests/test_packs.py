from aegis.packs import CompliancePack
from aegis.packs.sr117 import SR117_PACK
from aegis.policy import PolicyEngine


def _engine():
    return PolicyEngine(SR117_PACK.policies)


def test_pack_metadata():
    assert isinstance(SR117_PACK, CompliancePack)
    assert len(SR117_PACK.policies) == 5
    assert SR117_PACK.citation("sr117_model_inventory").startswith("SR 11-7")
    assert set(SR117_PACK.policy_names()) == set(SR117_PACK.references)


def test_unregistered_model_denied():
    r = _engine().evaluate({"model_id": "rogue-1", "registered_models": ["agent-a"]})
    assert r.verdict == "deny"
    assert "sr117_model_inventory" in r.triggered


def test_registered_model_allowed():
    r = _engine().evaluate({"model_id": "agent-a", "registered_models": ["agent-a"]})
    assert r.verdict == "allow"


def test_high_risk_without_validation_escalates():
    r = _engine().evaluate({"model_id": "agent-a", "registered_models": ["agent-a"],
                            "risk_tier": "high"})
    assert r.verdict == "escalate"
    assert "sr117_independent_validation" in r.triggered


def test_high_risk_with_validation_allowed():
    r = _engine().evaluate({"model_id": "agent-a", "registered_models": ["agent-a"],
                            "risk_tier": "high", "independently_validated": True})
    assert r.verdict == "allow"


def test_deployment_without_eval_evidence_denied():
    r = _engine().evaluate({"model_id": "agent-a", "registered_models": ["agent-a"],
                            "action_type": "agent_deployment"})
    assert r.verdict == "deny"
    assert "sr117_eval_gate_evidence" in r.triggered


def test_deployment_with_promote_allowed():
    r = _engine().evaluate({"model_id": "agent-a", "registered_models": ["agent-a"],
                            "action_type": "agent_deployment",
                            "eval_gate_verdict": "promote"})
    assert r.verdict == "allow"


def test_undocumented_material_change_escalates():
    r = _engine().evaluate({"model_id": "agent-a", "registered_models": ["agent-a"],
                            "material_change": True})
    assert r.verdict == "escalate"
    assert "sr117_change_documentation" in r.triggered


def test_unapproved_use_denied():
    r = _engine().evaluate({"model_id": "agent-a", "registered_models": ["agent-a"],
                            "use_case": "credit-decisions",
                            "approved_use_cases": ["support-triage"]})
    assert r.verdict == "deny"
    assert "sr117_approved_use" in r.triggered
