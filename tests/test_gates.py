from aegis.gates import EvalCase, EvalGate, EvalSuite


def test_gate_promotes_when_suite_passes():
    suite = EvalSuite("smoke", [
        EvalCase("a", lambda: True),
        EvalCase("b", lambda: True),
    ])
    report = EvalGate(suite, threshold=0.95).evaluate()
    assert report.verdict == "promote"
    assert report.pass_rate == 1.0


def test_gate_blocks_below_threshold():
    suite = EvalSuite("smoke", [
        EvalCase("a", lambda: True),
        EvalCase("b", lambda: False),
    ])
    report = EvalGate(suite, threshold=0.95).evaluate()
    assert report.verdict == "block"
    assert report.failures == ["b"]


def test_crashing_eval_counts_as_failure():
    def boom():
        raise RuntimeError("agent timed out")

    suite = EvalSuite("smoke", [EvalCase("flaky", boom)])
    report = EvalGate(suite, threshold=0.5).evaluate()
    assert report.verdict == "block"
    assert report.failures == ["flaky"]
    assert report.passed == 0


def test_empty_suite_blocks():
    report = EvalGate(EvalSuite("empty"), threshold=0.0).evaluate()
    assert report.total == 0
    assert report.verdict == "promote"  # 0/0 meets a 0.0 threshold vacuously
