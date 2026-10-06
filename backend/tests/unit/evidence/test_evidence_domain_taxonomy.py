from __future__ import annotations

import pytest

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.evidence.scholarly_adapter import (
    ScholarlyEvidenceAdapter,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.reasoning.contracts import (
    ReligiousDiscipline,
)
from basira.reasoning.routing import (
    _DISCIPLINE_DOMAINS,
)


@pytest.mark.parametrize(
    (
        "scholarly_domain",
        "evidence_domain",
    ),
    (
        (
            ScholarlyDomain.AQIDAH,
            EvidenceDomain.AQIDAH,
        ),
        (
            ScholarlyDomain.SIRA,
            EvidenceDomain.SIRA,
        ),
        (
            ScholarlyDomain.HISTORY,
            EvidenceDomain.HISTORY,
        ),
        (
            ScholarlyDomain.LANGUAGE,
            EvidenceDomain.LANGUAGE,
        ),
    ),
)
def test_scholarly_domain_identity_is_preserved(
    scholarly_domain,
    evidence_domain,
):
    passage = ScholarlyPassage(
        passage_id=(f"passage:{scholarly_domain.value}"),
        source_id="source:test",
        domain=scholarly_domain,
        work_id="work:test",
        work_title="Test Work",
        text="test evidence",
    )

    node = ScholarlyEvidenceAdapter().from_passage(passage)

    assert node.domain is evidence_domain


def test_general_remains_true_generic_domain():
    assert EvidenceDomain.GENERAL.value == "general"

    assert EvidenceDomain.AQIDAH is not EvidenceDomain.GENERAL

    assert EvidenceDomain.SIRA is not EvidenceDomain.GENERAL

    assert EvidenceDomain.HISTORY is not EvidenceDomain.GENERAL

    assert EvidenceDomain.LANGUAGE is not EvidenceDomain.GENERAL


def test_reasoning_aqidah_no_longer_targets_general():
    domains = _DISCIPLINE_DOMAINS[ReligiousDiscipline.AQIDAH]

    assert EvidenceDomain.AQIDAH in domains

    assert EvidenceDomain.GENERAL not in domains


def test_reasoning_sirah_no_longer_targets_general():
    domains = _DISCIPLINE_DOMAINS[ReligiousDiscipline.SIRAH]

    assert EvidenceDomain.SIRA in domains

    assert EvidenceDomain.GENERAL not in domains
