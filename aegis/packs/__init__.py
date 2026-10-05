"""Compliance packs: pre-built policy sets mapped to regulatory frameworks.

A pack bundles policies with their framework citations, so the audit trail
can show not just *what* was enforced but *which* regulatory expectation it
satisfies. Packs are plain data — review them like code, version them in git.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from aegis.policy import Policy


@dataclass
class CompliancePack:
    name: str
    framework: str
    version: str = "1.0"
    description: str = ""
    # policy name -> framework section citation, e.g. "SR 11-7, Model Validation"
    references: dict[str, str] = field(default_factory=dict)
    policies: list[Policy] = field(default_factory=list)

    def policy_names(self) -> list[str]:
        return [p.name for p in self.policies]

    def citation(self, policy_name: str) -> str:
        return self.references.get(policy_name, "")
