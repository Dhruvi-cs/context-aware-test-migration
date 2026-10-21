"""Kill-set preservation metrics (replacement for the paper's undefined Q_sem, Eq. 39).
K(T) = set of mutant ids that T kills: T passes on the original app AND fails on the mutant."""
from typing import Iterable, Optional


def kill_set(passes_original: bool, failed_mutants: Iterable[str]) -> set:
    return set(failed_mutants) if passes_original else set()


def ksp(k_src: set, k_tgt: set) -> Optional[float]:
    """|K(Ts) & K(Tt)| / |K(Ts)|. None when K(Ts) is empty (test excluded by design)."""
    return len(k_src & k_tgt) / len(k_src) if k_src else None


def spurious_kill_rate(k_src: set, k_tgt: set) -> Optional[float]:
    """|K(Tt) \\ K(Ts)| / |K(Tt)|. Needs a flake re-run before being interpreted."""
    return len(k_tgt - k_src) / len(k_tgt) if k_tgt else None


def silent_degradation_rate(rows, threshold: float = 1.0) -> Optional[float]:
    """Share of migrated tests that PASS on the original app yet have KSP < threshold.
    rows: iterable of (passes_original: bool, ksp_value: Optional[float]); None-KSP rows are skipped."""
    rows = [(p, k) for p, k in rows if k is not None]
    passing = [(p, k) for p, k in rows if p]
    return sum(1 for _, k in passing if k < threshold) / len(passing) if passing else None
