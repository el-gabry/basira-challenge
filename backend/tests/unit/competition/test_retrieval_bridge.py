from __future__ import annotations

import pytest

from basira.competition.madhhab_authority import (
    MadhhabBookRetrievalMode,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionAuthorityBoundaryError,
    CompetitionMaterialRole,
    CompetitionPolicyRequired,
    CompetitionRetrievalBridge,
    CompetitionRetrievalRequest,
    CompetitionSourceMaterial,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.retrieval.fiqh_policy_compiler import (
    FiqhRetrievalPolicyEnvelope,
)


class RecordingEvidenceAdapter:
    def __init__(
        self,
        domain: EvidenceDomain,
    ) -> None:
        self.domain = domain
        self.requests = []

    def retrieve(
        self,
        request,
    ):
        self.requests.append(request)

        return (
            EvidenceNode(
                evidence_id=("test:" + self.domain.value),
                domain=self.domain,
                text="governed evidence",
                source_id="test-source",
            ),
        )


class RecordingMaterialAdapter:
    def __init__(
        self,
        role: CompetitionMaterialRole,
    ) -> None:
        self.role = role
        self.requests = []

    def retrieve(
        self,
        request,
    ):
        self.requests.append(request)

        return (
            CompetitionSourceMaterial(
                material_id=("material:" + self.role.value),
                source_id="test-source",
                role=self.role,
                text="governed material",
            ),
        )


def fiqh_policy() -> FiqhRetrievalPolicyEnvelope:
    return FiqhRetrievalPolicyEnvelope(
        requested_madhhabs=("hanafi",),
        retrieval_mode=(MadhhabBookRetrievalMode.MUTAMAD_ONLY),
        primary_work_ids=("1045",),
        supporting_work_ids=(),
        forbidden_fallbacks=(
            "generic_shamela_fallback",
            "ungoverned_web_fallback",
        ),
        policy_fingerprint=("a" * 64),
    )


def test_quran_uses_explicit_competition_domain() -> None:
    adapter = RecordingEvidenceAdapter(EvidenceDomain.QURAN)

    bridge = CompetitionRetrievalBridge(
        evidence_adapters={
            OfficialDomain.QURAN: adapter,
        }
    )

    result = bridge.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.QURAN),
            query="ما نص الآية 2:255؟",
        )
    )

    assert result.unavailable is False

    assert result.evidence[0].domain is EvidenceDomain.QURAN

    assert result.materials == ()

    assert adapter.requests[0].official_domain is OfficialDomain.QURAN


def test_missing_domain_adapter_fails_closed() -> None:
    bridge = CompetitionRetrievalBridge()

    result = bridge.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.DAWAH_GENERAL_CONTENT),
            query="سؤال عام",
        )
    )

    assert result.evidence == ()
    assert result.materials == ()
    assert result.unavailable is True

    assert result.unavailable_reason == "evidence_adapter_unavailable"


def test_fiqh_requires_policy_envelope() -> None:
    adapter = RecordingEvidenceAdapter(EvidenceDomain.FIQH)

    bridge = CompetitionRetrievalBridge(
        evidence_adapters={
            OfficialDomain.GENERAL_FIQH: adapter,
        }
    )

    with pytest.raises(CompetitionPolicyRequired):
        bridge.retrieve(
            CompetitionRetrievalRequest(
                official_domain=(OfficialDomain.GENERAL_FIQH),
                query="ما حكم الشفعة؟",
            )
        )

    assert adapter.requests == []


def test_fiqh_policy_reaches_adapter_unchanged() -> None:
    policy = fiqh_policy()

    adapter = RecordingEvidenceAdapter(EvidenceDomain.FIQH)

    bridge = CompetitionRetrievalBridge(
        evidence_adapters={
            OfficialDomain.GENERAL_FIQH: adapter,
        }
    )

    result = bridge.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.GENERAL_FIQH),
            query="ما حكم الشفعة؟",
            fiqh_policy=policy,
        )
    )

    assert result.unavailable is False

    assert adapter.requests[0].fiqh_policy is policy

    assert result.evidence[0].domain is EvidenceDomain.FIQH


@pytest.mark.parametrize(
    (
        "domain",
        "role",
    ),
    (
        (
            OfficialDomain.SHUBUHAT_FAQ,
            CompetitionMaterialRole.CONVERSATIONAL,
        ),
        (
            OfficialDomain.TRANSLATION_TERMINOLOGY,
            CompetitionMaterialRole.TERMINOLOGY,
        ),
    ),
)
def test_non_primary_domains_stay_material_only(
    domain,
    role,
) -> None:
    adapter = RecordingMaterialAdapter(role)

    bridge = CompetitionRetrievalBridge(
        material_adapters={
            domain: adapter,
        }
    )

    result = bridge.retrieve(
        CompetitionRetrievalRequest(
            official_domain=domain,
            query="test",
        )
    )

    assert result.unavailable is False
    assert result.evidence == ()

    assert result.materials[0].role is role


@pytest.mark.parametrize(
    "domain",
    (
        OfficialDomain.SHUBUHAT_FAQ,
        (OfficialDomain.TRANSLATION_TERMINOLOGY),
    ),
)
def test_material_only_domain_cannot_become_primary_evidence(
    domain,
) -> None:
    adapter = RecordingEvidenceAdapter(EvidenceDomain.GENERAL)

    with pytest.raises(CompetitionAuthorityBoundaryError):
        CompetitionRetrievalBridge(
            evidence_adapters={
                domain: adapter,
            }
        )


def test_request_rejects_blank_query() -> None:
    with pytest.raises(
        ValueError,
        match="nonblank",
    ):
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.QURAN),
            query="   ",
        )


def test_request_rejects_nonpositive_limit() -> None:
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.QURAN),
            query="2:255",
            limit=0,
        )


def test_source_unavailable_is_not_treated_as_zero_hits():
    from basira.competition.retrieval_bridge import (
        CompetitionSourceUnavailable,
    )

    class BrokenEvidenceAdapter:
        def retrieve(
            self,
            request,
        ):
            raise CompetitionSourceUnavailable("dorar_hadith")

    bridge = CompetitionRetrievalBridge(
        evidence_adapters={
            OfficialDomain.HADITH: BrokenEvidenceAdapter(),
        }
    )

    result = bridge.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.HADITH),
            query="حديث",
        )
    )

    assert result.evidence == ()
    assert result.materials == ()
    assert result.unavailable is True

    assert result.unavailable_reason == "source_unavailable:dorar_hadith"
