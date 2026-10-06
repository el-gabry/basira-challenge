from __future__ import annotations

import unicodedata
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
from basira.sources.hadith.grade_normalization import (
    categorize_hadith_grade,
)


def _hadith_text_is_visibly_truncated(
    value: str,
) -> bool:
    """
    Refuse source snippets that visibly declare themselves
    incomplete.

    Basira must never remove an ellipsis and pretend a partial
    hadith is a complete matn.
    """

    normalized = " ".join(value.split())

    if not normalized:
        return True

    markers = (
        "...",
        "…",
        ". . .",
        "الحَديث",
        "الحديث...",
        "الحديث …",
    )

    return any(
        marker in normalized
        for marker in markers
    )


DORAR_HADITH_SOURCE_ID = "dorar-hadith-live-v1"


def _clean(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = " ".join(value.split())

    return value or None


def _normalize_hadith_identity_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ة": "ه",
    }

    chars: list[str] = []

    for char in value:
        if char == "\u0640":
            continue

        if unicodedata.category(char) in {
            "Mn",
            "Me",
            "Cf",
        }:
            continue

        char = replacements.get(
            char,
            char,
        )

        if char.isalnum() or char.isspace():
            chars.append(char)
        else:
            chars.append(" ")

    return " ".join("".join(chars).split())


def _hadith_grade_group(
    record: DorarHadithRecord,
) -> str:
    """
    Comparison identity only.

    Same normalized matn + narrator may have multiple
    attributed scholarly gradings.

    Different narrators/routes remain separate groups.
    """

    matn = _normalize_hadith_identity_text(record.hadith_text)

    narrator = _normalize_hadith_identity_text(record.narrator)

    payload = f"{narrator}\n{matn}"

    digest = sha256(payload.encode("utf-8")).hexdigest()[:24]

    return f"dorar-hadith-grade:{digest}"


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
            full_text_search = getattr(
                self._retriever,
                "search_full_text",
                None,
            )

            if callable(full_text_search):
                result = full_text_search(
                    request.query,
                    limit=request.limit,
                )
            else:
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

        records = sorted(
            result.records,
            key=lambda item: len(
                " ".join(
                    item.hadith_text.split()
                )
            ),
            reverse=True,
        )

        admitted_records = []

        for record in records:
            # A Dorar HTML article may legitimately be short.
            # We reject only explicit abbreviation markers here.
            if _hadith_text_is_visibly_truncated(
                record.hadith_text
            ):
                continue

            candidate = record_to_candidate(
                record
            )

            assessment = self._policy.assess(
                candidate
            )

            if not _policy_allows_evidence(
                assessment.decision
            ):
                continue

            admitted_records.append(
                record
            )

        if not admitted_records:
            return ()

        # Publicly publish one canonical matn only.
        #
        # search_full_text() has already proven each hydrated
        # record against an official Dorar HTML article. From
        # the admitted set we prefer the most complete article,
        # avoiding a UI filled with shorter variants/snippets.
        canonical_record = max(
            admitted_records,
            key=lambda item: len(
                " ".join(
                    item.hadith_text.split()
                )
            ),
        )

        canonical_reference = _record_reference(
            canonical_record
        )

        canonical_base_id = sha256(
            (
                canonical_reference
                + "\n"
                + canonical_record.hadith_text
            ).encode(
                "utf-8"
            )
        ).hexdigest()[:24]

        canonical_text_id = (
            f"dorar-hadith:"
            f"{canonical_base_id}:text"
        )

        canonical_text_key = " ".join(
            canonical_record.hadith_text.split()
        )

        nodes = [
            EvidenceNode(
                evidence_id=canonical_text_id,
                domain=EvidenceDomain.HADITH,
                text=canonical_record.hadith_text,
                source_id=DORAR_HADITH_SOURCE_ID,
                reference=canonical_reference,
                author_name=(
                    _clean(
                        canonical_record.narrator
                    )
                ),
                claim_type="hadith_text",
            )
        ]

        # Preserve admitted grading evidence. A grade is linked
        # to the canonical matn only when its Dorar article text
        # is exactly the same canonical text. Otherwise it stays
        # standalone rather than claiming a relationship that
        # the source does not prove.
        for record in admitted_records:
            verdict = _clean(
                record.verdict
            )

            if verdict is None:
                continue

            reference = _record_reference(
                record
            )

            base_id = sha256(
                (
                    reference
                    + "\n"
                    + record.hadith_text
                ).encode(
                    "utf-8"
                )
            ).hexdigest()[:24]

            record_text_key = " ".join(
                record.hadith_text.split()
            )

            related_hadith = (
                (canonical_text_id,)
                if record_text_key
                == canonical_text_key
                else ()
            )

            nodes.append(
                EvidenceNode(
                    evidence_id=(
                        f"dorar-hadith:"
                        f"{base_id}:grade"
                    ),
                    domain=EvidenceDomain.HADITH,
                    text=verdict,
                    source_id=(
                        DORAR_HADITH_SOURCE_ID
                    ),
                    reference=reference,
                    author_name=(
                        _clean(
                            record.muhaddith
                        )
                    ),
                    topic=(
                        categorize_hadith_grade(
                            verdict
                        ).value
                    ),
                    claim_type="hadith_grade",
                    related_hadith=(
                        related_hadith
                    ),
                    conflict_group=(
                        _hadith_grade_group(
                            record
                        )
                    ),
                )
            )

        return tuple(nodes)
