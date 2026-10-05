# Aegis — Governance Layer for Production AI Agents

Aegis is the control plane for AI agents operating in regulated industries. It answers the question every compliance team asks before an agent goes live: **"Prove to me this agent behaved."**

## The problem

Enterprises are deploying AI agents into customer-facing workflows, but governance hasn't caught up. Model risk teams need audit trails, policy enforcement, and human-override records. Today that's built by hand, per deployment, and it doesn't scale.

## What Aegis does

1. **Policy engine** — Declare rules agents must obey in plain config: "never send customer PII to external tools", "financial recommendations require human approval", "cap autonomous spend at $X per session". Policies are versioned and evaluable.
2. **Immutable audit trail** — Every agent action, tool call, and decision is logged with timestamps, inputs, outputs, and the policy verdict. Append-only; tampering is detectable.
3. **Eval gates** — Block agent promotion unless the eval suite passes. Every deployment is measured against a golden dataset before it touches production traffic.
4. **Human-in-the-loop approvals** — Flagged actions pause for human review with full context. Overrides are logged with who approved and why.
5. **Compliance reports** — Export model-risk-style documentation: what the agent did, what rules applied, what was overridden, and the eval evidence. The artifact a regulator or risk committee actually wants to read.

## Status

All five modules built. Run `python -m aegis.demo` to see the full loop:
policy verdicts, the human approval, an eval gate, and a generated
compliance report.

## Quickstart

```bash
pip install -e .
python -m aegis.demo
```

## Design principles

- **Local-first.** Your agent's audit data never leaves your machine unless you say so.
- **Boring technology.** SQLite, plain Python, no magic. A compliance tool must be auditable itself.
- **Eval everything.** Every policy change ships with tests proving it behaves.
