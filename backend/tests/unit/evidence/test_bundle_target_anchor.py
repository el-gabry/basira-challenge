from __future__ import annotations

from types import SimpleNamespace

from basira.evidence.bundle import EvidenceBundleBuilder
from basira.evidence.models import EvidenceDomain


def test_target_reference_is_exact_quran_anchor() -> None:
    result = SimpleNamespace(
        plan=SimpleNamespace(
            targets=(
                SimpleNamespace(
                    domain=EvidenceDomain.QURAN,
                    references=("2:255",),
                ),
            ),
            understanding=SimpleNamespace(
                entities=(),
            ),
        ),
    )

    assert EvidenceBundleBuilder._has_exact_quran_anchor(result)
