"""Eval gates: block agent promotion unless the eval suite passes.

Every deployment is measured against a golden dataset before it touches
production traffic. A gate defines the bar (e.g. 95% pass rate); anything
below it is blocked and the decision is written to the audit trail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class EvalCase:
    name: str
    run: Callable[[], bool]
    detail: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    name: str
    passed: bool
    detail: dict = field(default_factory=dict)


@dataclass
class GateReport:
    suite: str
    total: int
    passed: int
    pass_rate: float
    threshold: float
    verdict: str  # "promote" | "block"
    failures: list[str] = field(default_factory=list)


class EvalSuite:
    def __init__(self, name: str, cases: list[EvalCase] | None = None):
        self.name = name
        self.cases: list[EvalCase] = list(cases or [])

    def add(self, case: EvalCase) -> None:
        self.cases.append(case)

    def run(self) -> list[EvalResult]:
        results = []
        for case in self.cases:
            try:
                passed = bool(case.run())
                detail: dict = {}
            except Exception as exc:  # noqa: BLE001 — a crashing eval is a failed eval
                passed = False
                detail = {"error": str(exc)}
            results.append(EvalResult(case.name, passed, {**case.detail, **detail}))
        return results


class EvalGate:
    """Decides promote vs block for one suite at one threshold."""

    def __init__(self, suite: EvalSuite, threshold: float = 0.95):
        self.suite = suite
        self.threshold = threshold

    def evaluate(self) -> GateReport:
        results = self.suite.run()
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        rate = (passed / total) if total else 0.0
        verdict = "promote" if rate >= self.threshold else "block"
        return GateReport(
            suite=self.suite.name,
            total=total,
            passed=passed,
            pass_rate=round(rate, 4),
            threshold=self.threshold,
            verdict=verdict,
            failures=[r.name for r in results if not r.passed],
        )
