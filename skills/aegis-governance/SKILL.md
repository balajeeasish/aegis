---
name: aegis-governance
description: Governance for production AI agents — policy enforcement, hash-chained audit trails, human approvals, eval gates, and compliance reports. Use when an agent takes trust-sensitive actions, when a deployment needs proof it behaved, or when building agents for regulated industries (financial services, healthcare, public sector). Use for SR 11-7-style model-risk evidence, PII/spend guardrails, and approval workflows.
---

# Aegis Governance

Aegis is a local-first Python library that answers one question before an
agent goes live: "Prove to me this agent behaved."

It does not run your agent, call a model, or stop a tool call by itself.
It returns verdicts — allow, deny, escalate — and a durable record. Your
host code must enforce the verdict before the side effect happens.

## Install

```bash
git clone https://github.com/balajeeasish/aegis.git
cd aegis
pip install -e .
python -m aegis.demo
```

Zero runtime dependencies. Python 3.10+. MIT licensed.

Install as an agent skill (same layout as Cloudflare's security-audit skill):

```bash
npx skills add https://github.com/balajeeasish/aegis --skill aegis-governance
```

## The 10-line version

```python
from aegis import AuditLog, ApprovalQueue, PolicyEngine, STANDARD_POLICIES

log = AuditLog("audit.jsonl")
engine = PolicyEngine(STANDARD_POLICIES)
queue = ApprovalQueue(log)

detail = {"tool": "webhook", "tool_external": True,
          "payload": "notify ssn: 123-45-6789", "pii_markers": ["ssn:"]}
result = engine.evaluate(detail)  # deny: no_pii_to_external_tools
log.record("support-agent", "tool_call", detail, result.verdict)
# Host rule: only run the tool if result.verdict == "allow".
# If "escalate", open an approval instead of running it.
```

Run the demo for the full loop — policy verdicts, a human approval, an
eval gate, and a generated compliance report:

```bash
python -m aegis.demo
# report: /tmp/aegis-demo-report.md
```

## The five modules

### 1. Policy engine — `aegis.policy`

```python
from aegis import Policy, PolicyEngine

engine = PolicyEngine([
    Policy(name="no_external_pii", condition=lambda d: d.get("tool_external")
           and "ssn:" in str(d.get("payload", "")), verdict="deny"),
])
result = engine.evaluate(detail)
result.verdict        # "allow" | "deny" | "escalate"
result.triggered      # ["no_external_pii"]
result.errors         # policies whose condition raised, if any
```

Built-ins (`STANDARD_POLICIES`): `no_pii_to_external_tools` (deny),
`financial_advice_needs_approval` (escalate),
`spend_cap` (deny).

**Fail-closed rule — do not weaken this.** If a policy condition raises,
Aegis treats it as triggered, using that policy's own verdict, and records
the error in `result.errors`. A broken policy must never silently allow an
action. If you see `result.errors` non-empty, fix the policy; do not strip
the error and proceed.

**Trusted-context rule — the most important rule in this skill.** Every
policy reads its decisive fact from the `detail` dict you pass in:
`human_approved`, `spend_cap_usd`, `pii_markers`, `registered_models`,
`independently_validated`, `eval_gate_verdict`, `approved_use_cases`.
Aegis cannot tell a trusted host fact from an agent-supplied claim, so
**never pass agent-supplied values for those fields**. Build `detail`
from host-owned sources — your registry, your gate run, your approval
record — not from the agent's own output. Passing
`{"human_approved": True}` because the agent said so defeats the control.

`no_pii_to_external_tools` is marker-based: it fires only when a
caller-supplied `pii_markers` entry appears in the payload. It is a
host-labelling check, not a PII detector. For real PII coverage, inspect
structured payloads before serialisation or add a detector in the host.

### 2. Audit trail — `aegis.audit`

```python
from aegis import AuditLog

log = AuditLog("audit.jsonl")
entry = log.record("support-agent", "tool_call", detail, result.verdict)
ok, msg = log.verify()  # (True, "chain intact (5 entries)")
```

Every entry is SHA-256 hash-chained to the previous one and stored as
JSONL. `verify()` detects naive edits that do not recompute hashes.

**Honest limit.** The chain is unkeyed with a known genesis, so anyone
with write access to the JSONL file can rewrite history and recompute
the hashes. Treat the log as tamper-evident against accidental or naive
edits, not as proof against a determined file writer. For evidence you
will show a regulator, HMAC the chain with a key held outside the file
or anchor the head hash externally, set restrictive file permissions,
and remember the log stores payloads verbatim — including any PII or
secrets in `detail` — so protect it like the data it records.

### 3. Human approvals — `aegis.approvals`

```python
from aegis import ApprovalQueue

queue = ApprovalQueue(log)  # default TTL: 3600 seconds
req = queue.request(actor, action, detail, result.triggered)
queue.approve(req.id, by="risk-officer", reason="client confirmed in writing")
queue.decline(req.id, by="risk-officer", reason="too aggressive")
```

Rules: a request can be decided once (a second decision raises
`ValueError`); an unknown id raises `KeyError`; **expiry is enforced at
decision time** — approving an already-expired request raises
`ValueError` and records it as expired. `by` is a plain string: Aegis
provides no authentication, so the host must authenticate the approver
before calling `approve()`. The queue itself is in-memory; the audit log
is the durable record.

### 4. Eval gates — `aegis.gates`

```python
from aegis import EvalCase, EvalGate, EvalSuite

suite = EvalSuite("release-smoke", [
    EvalCase("no-pii-leak", lambda: True),
    EvalCase("spend-cap-honored", lambda: True),
])
gate = EvalGate(suite, threshold=0.95).evaluate()
gate.verdict  # "promote" | "block"
```

A crashing eval counts as a failure, not a pass. An empty suite blocks
(rate 0.0). Eval cases are arbitrary host callables run in-process —
keep them developer-written and reviewed like code, never
model-generated or loaded from untrusted sources.

### 5. Compliance reports — `aegis.reports`

```python
from aegis import generate

report = generate(log, [gate], title="Aegis Compliance Report")
```

The report renders verdict counts, policy triggers, approval/override
records with who approved and why, eval-gate evidence, and chain
integrity. It is a rendering of the audit log, not a second source of
truth. Escape or validate approval reasons before rendering in a
consumer that interprets Markdown/HTML: report fields are interpolated
verbatim.

## Compliance packs — `aegis.packs`

```python
from aegis import PolicyEngine, STANDARD_POLICIES, SR117_PACK

engine = PolicyEngine(SR117_PACK.policies + STANDARD_POLICIES)
```

`SR117_PACK` maps Federal Reserve SR 11-7 model-risk expectations to
enforceable policies: model inventory (`sr117_model_inventory`, deny),
independent validation for high-risk changes
(`sr117_independent_validation`, escalate), eval-gate evidence for
deployments (`sr117_eval_gate_evidence`, deny), change documentation
(`sr117_change_documentation`, escalate), and approved-use restrictions
(`sr117_approved_use`, deny). This is a practitioner's mapping, not
legal advice. Each policy cites the SR 11-7 element it serves in
`SR117_PACK.references`.

## Checklist before you ship an Aegis-governed agent

- [ ] Host enforces every verdict before the side effect; Aegis alone
      does not block anything.
- [ ] `detail` fields that decide policy come from trusted host sources,
      never from agent output.
- [ ] Approvers are authenticated by the host before `approve()` is called.
- [ ] Audit file permissions, retention, and (for regulator evidence)
      HMAC/anchoring are set by the deployment.
- [ ] Eval cases and policy conditions are developer code, reviewed
      like code.
- [ ] No tenant is sharing one `AuditLog`/`ApprovalQueue` instance —
      Aegis has no tenant field or owner check.

## What Aegis is not

Not a model, not a firewall, not an auth system, not a PII detector, and
not a replacement for enterprise GRC. It is the developer-owned evidence
layer underneath those: policy, audit, approval, gate, report — local,
boring, auditable itself.
