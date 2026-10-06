from __future__ import annotations

from hashlib import sha256

from basira.competition.dorar_hadith import (
    DorarHadithRecord,
)
from basira.competition.dorar_hadith_retrieval import (
    DorarHadithRetriever,
)
from basira.competition.hadith_policy import (
    HadithAttestation,
    HadithEvidenceCandidate,
    HadithEvidenceDecision,
    HadithVerificationAuthority,
    OfficialHadithPolicy,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
    CompetitionSourceUnavailable,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)

DORAR_HADITH_SOURCE_ID = "dorar-hadith-live-v1"


def _clean(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = " ".join(value.split())

    return value or None


def _record_reference(
    record: DorarHadithRecord,
) -> str:
    parts = tuple(
        value
        for value in (
            _clean(record.source),
            _clean(record.page_or_number),
        )
        if value
    )

    if parts:
        return " | ".join(parts)

    rank = str(record.rank) if record.rank is not None else "unranked"

    digest = sha256(record.hadith_text.encode("utf-8")).hexdigest()[:16]

    return f"dorar:{rank}:{digest}"


def _record_attestation(
    record: DorarHadithRecord,
) -> HadithAttestation | None:
    verdict = _clean(record.verdict)

    if verdict is None:
        return None

    payload = {
        "verification_authority": (HadithVerificationAuthority.DORAR),
        "verdict": verdict,
        "muhaddith": record.muhaddith,
        "reference": record.page_or_number,
    }

    # Do not invent absent attribution.
    return HadithAttestation(
        **{key: value for key, value in payload.items() if value is not None}
    )


def record_to_candidate(
    record: DorarHadithRecord,
) -> HadithEvidenceCandidate:
    attestation = _record_attestation(record)

    return HadithEvidenceCandidate(
        hadith_text=(record.hadith_text),
        claimed_collection=(_clean(record.source)),
        collection_reference=(_clean(record.page_or_number)),
        narrator=(_clean(record.narrator)),
        governed_canonical_source=False,
        attestations=((attestation,) if attestation is not None else ()),
    )


def _decision_value(
    decision: HadithEvidenceDecision,
) -> str:
    return str(
        getattr(
            decision,
            "value",
            decision,
        )
    ).lower()


def _policy_allows_evidence(
    decision: HadithEvidenceDecision,
) -> bool:
    """
    Dorar records may enter the evidence lane only
    when OfficialHadithPolicy explicitly returns its
    attributed-grading usable state.

    Do not infer usability from generic wording.
    """

    return decision is HadithEvidenceDecision("usable_with_attributed_gradings")


class DorarHadithEvidenceAdapter:
    """
    Competition Hadith lane:

      request
      -> Dorar source retrieval
      -> Dorar record
      -> HadithEvidenceCandidate
      -> OfficialHadithPolicy
      -> source-derived EvidenceNodes

    No majority vote.
    No invented consensus.
    No unsupported grading normalization.
    """

    def __init__(
        self,
        *,
        retriever: DorarHadithRetriever,
        policy: (OfficialHadithPolicy | None) = None,
    ) -> None:
        self._retriever = retriever
        self._policy = policy or OfficialHadithPolicy()

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        try:
            result = self._retriever.search(
                request.query,
                limit=request.limit,
            )
        except Exception as exc:
            from basira.competition.dorar_hadith_retrieval import (
                DorarHadithPayloadError,
            )
            from basira.competition.dorar_transport import (
                DorarTransportError,
            )

            if isinstance(
                exc,
                (
                    DorarTransportError,
                    DorarHadithPayloadError,
                ),
            ):
                raise CompetitionSourceUnavailable("dorar_hadith") from exc

            raise

        nodes = []

        for record in result.records:
            candidate = record_to_candidate(record)

            assessment = self._policy.assess(candidate)

            if not _policy_allows_evidence(assessment.decision):
                continue

            reference = _record_reference(record)

            base_id = sha256(
                (reference + "\n" + record.hadith_text).encode("utf-8")
            ).hexdigest()[:24]

            nodes.append(
                EvidenceNode(
                    evidence_id=(f"dorar-hadith:{base_id}:text"),
                    domain=(EvidenceDomain.HADITH),
                    text=(record.hadith_text),
                    source_id=(DORAR_HADITH_SOURCE_ID),
                    reference=reference,
                    author_name=(_clean(record.narrator)),
                    claim_type=("hadith_text"),
                )
            )

            verdict = _clean(record.verdict)

            if verdict is not None:
                nodes.append(
                    EvidenceNode(
                        evidence_id=(f"dorar-hadith:{base_id}:grade"),
                        domain=(EvidenceDomain.HADITH),
                        text=verdict,
                        source_id=(DORAR_HADITH_SOURCE_ID),
                        reference=reference,
                        author_name=(_clean(record.muhaddith)),
                        claim_type=("hadith_grade"),
                        related_hadith=((f"dorar-hadith:{base_id}:text"),),
                    )
                )

        return tuple(nodes)
