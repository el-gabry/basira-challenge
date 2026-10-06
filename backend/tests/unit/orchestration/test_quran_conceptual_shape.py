from types import SimpleNamespace
from typing import cast

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.orchestration.contracts import (
    ClaimTask,
)
from basira.orchestration.evidence_acceptance import (
    RetrievalShape,
)
from basira.orchestration.evidence_contract_compiler import (
    _retrieval_shape,
)
from basira.reasoning.contracts import (
    ReasoningMode,
)


def test_conceptual_quran_without_hard_anchor_is_conceptual() -> None:
    task = cast(
        ClaimTask,
        SimpleNamespace(
            frame=SimpleNamespace(
                reasoning_mode=(
                    ReasoningMode.CONCEPTUAL_GROUNDING
                ),
            ),
        ),
    )

    result = _retrieval_shape(
        task,
        anchors=(),
        allowed_domains=frozenset(
            {
                EvidenceDomain.QURAN,
            }
        ),
    )

    assert result is RetrievalShape.CONCEPTUAL
