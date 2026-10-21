import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mig_eval.metrics import *

def test_metrics():
    assert kill_set(False, {"a"}) == set() and kill_set(True, ["a", "b"]) == {"a", "b"}
    assert ksp({"a", "b"}, {"a", "b", "c"}) == 1.0
    assert ksp({"a", "b"}, {"a"}) == 0.5 and ksp({"a"}, set()) == 0.0
    assert ksp(set(), {"a"}) is None
    assert spurious_kill_rate({"a"}, {"a", "b"}) == 0.5 and spurious_kill_rate({"a"}, set()) is None
    rows = [(True, 1.0), (True, 0.5), (True, 0.0), (False, 0.0), (True, None)]
    assert abs(silent_degradation_rate(rows) - 2 / 3) < 1e-9       # 2 of 3 passing tests degraded
    assert silent_degradation_rate(rows, 0.5) == 1 / 3             # relaxed threshold
    assert silent_degradation_rate([(False, 0.2)]) is None
    print("metrics: all assertions passed")

if __name__ == "__main__":
    test_metrics()
