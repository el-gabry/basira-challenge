from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from basira.competition.hadith_policy import (
    HadithEvidenceDecision,
    HadithVerificationState,
    OfficialHadithPolicy,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)

SOURCE_ID = "dorar:hadith:en"
EVIDENCE_SOURCE_ID = "dorar-hadith-live-v1"
PROVIDER = "Dorar al-Sunniyyah"

PASSPORT_PATH = Path(
    "data/competition/passports/"
    "dorar-hadith-en.json"
)

MANIFEST_PATH = Path(
    "data/competition/manifests/hadith/"
    "dorar-hadith-en-captured-v1.json"
)

AUDIT_PATH = Path(
    "data/competition/audits/hadith/"
    "dorar-hadith-en-adversarial-v1.json"
)

_CANONICAL_URL = (
    "https://dorar.net/en/ahadith/45"
)

_COLLECTION_HEADING = "Bukhari hadiths"
_CANONICAL_COLLECTION = "Sahih al-Bukhari"

_ENGLISH_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "are",
        "authentic",
        "authenticity",
        "by",
        "correct",
        "did",
        "does",
        "hadith",
        "is",
        "it",
        "judged",
        "narration",
        "narrated",
        "report",
        "sahih",
        "saying",
        "the",
        "this",
        "true",
        "was",
        "were",
    }
)


class DorarEnglishHadithAdmissionError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class DorarEnglishHadithRecord:
    canonical_url: str
    article_id: str
    hadith_number: str
    collection_heading: str
    canonical_collection: str
    hadith_text: str
    response_sha256: str


@dataclass(
    frozen=True,
    slots=True,
)
class _PolicyCandidate:
    hadith_text: str
    claimed_collection: str | None
    collection_reference: str | None
    governed_canonical_source: bool
    no_hits_for_query: bool = False
    attestations: tuple[object, ...] = ()


class _EvidenceAdapter(Protocol):
    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[EvidenceNode, ...]: ...


def _load_json(
    path: Path,
) -> dict[str, object]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise DorarEnglishHadithAdmissionError(
            "english_hadith_governance_not_object"
        )

    return value


def _visible_text(
    value: str,
) -> str:
    value = re.sub(
        r"<script[\s\S]*?</script>",
        " ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"<style[\s\S]*?</style>",
        " ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    return " ".join(
        html.unescape(value).split()
    )


def _tokens(
    value: str,
) -> frozenset[str]:
    words = re.findall(
        r"[a-z0-9]+",
        value.casefold(),
    )

    return frozenset(
        word
        for word in words
        if (
            len(word) >= 3
            and word
            not in _ENGLISH_STOPWORDS
        )
    )


def _query_matches(
    *,
    query: str,
    hadith_text: str,
) -> bool:
    query_tokens = _tokens(
        query
    )

    if len(query_tokens) < 2:
        return False

    hadith_tokens = _tokens(
        hadith_text
    )

    overlap = (
        query_tokens
        & hadith_tokens
    )

    return (
        len(overlap) >= 2
        and (
            len(overlap)
            / len(query_tokens)
        ) >= 0.60
    )


def _parse_record(
    *,
    body: bytes,
    canonical_url: str,
    response_sha256: str,
) -> DorarEnglishHadithRecord:
    try:
        document = body.decode(
            "utf-8",
            errors="strict",
        )
    except UnicodeDecodeError as exc:
        raise (
            DorarEnglishHadithAdmissionError(
                "english_hadith_not_utf8"
            )
        ) from exc

    canonical_pattern = re.compile(
        r'<link[^>]+rel=["\']canonical["\']'
        r'[^>]+href=["\']'
        + re.escape(canonical_url)
        + r'["\'][^>]*>',
        flags=re.I,
    )

    if canonical_pattern.search(
        document
    ) is None:
        raise DorarEnglishHadithAdmissionError(
            "english_hadith_canonical_link_mismatch"
        )

    heading_pattern = re.compile(
        r"<h4\b[^>]*>"
        r"[\s\S]*?"
        r"Bukhari\s+hadiths"
        r"[\s\S]*?"
        r"</h4>",
        flags=re.I,
    )

    heading = heading_pattern.search(
        document
    )

    if heading is None:
        raise DorarEnglishHadithAdmissionError(
            "english_hadith_collection_heading_missing"
        )

    tail = document[
        heading.end():
    ]

    card = re.search(
        r"<h5\b[^>]*>"
        r"[\s\S]*?"
        r"<a\b[^>]*>"
        r"(?P<text>[\s\S]*?)"
        r"</a>"
        r"[\s\S]*?"
        r"</h5>",
        tail,
        flags=re.I,
    )

    if card is None:
        raise DorarEnglishHadithAdmissionError(
            "english_hadith_card_missing"
        )

    title = _visible_text(
        card.group("text")
    )

    match = re.fullmatch(
        r"(?P<number>\d+)"
        r"\s*-\s*"
        r"(?P<matn>.+)",
        title,
    )

    if match is None:
        raise DorarEnglishHadithAdmissionError(
            "english_hadith_number_or_matn_missing"
        )

    hadith_number = (
        match.group("number")
    )

    hadith_text = (
        match.group("matn").strip()
    )

    if (
        not hadith_text
        or "Commentary :"
        in hadith_text
    ):
        raise DorarEnglishHadithAdmissionError(
            "english_hadith_matn_boundary_invalid"
        )

    return DorarEnglishHadithRecord(
        canonical_url=canonical_url,
        article_id="45",
        hadith_number=hadith_number,
        collection_heading=(
            _COLLECTION_HEADING
        ),
        canonical_collection=(
            _CANONICAL_COLLECTION
        ),
        hadith_text=hadith_text,
        response_sha256=(
            response_sha256
        ),
    )


class DorarEnglishHadithRuntimeGate:
    def __init__(
        self,
        *,
        repo_root: Path | str,
    ) -> None:
        self.repo_root = Path(
            repo_root
        ).resolve()

        self.passport = _load_json(
            self.repo_root
            / PASSPORT_PATH
        )

        self.manifest = _load_json(
            self.repo_root
            / MANIFEST_PATH
        )

        self.audit = _load_json(
            self.repo_root
            / AUDIT_PATH
        )

        self._validate_governance()

    def _validate_governance(
        self,
    ) -> None:
        for artifact in (
            self.passport,
            self.manifest,
            self.audit,
        ):
            if (
                artifact.get("source_id")
                != SOURCE_ID
            ):
                raise (
                    DorarEnglishHadithAdmissionError(
                        "english_hadith_source_identity_mismatch"
                    )
                )

            if (
                artifact.get("provider")
                != PROVIDER
            ):
                raise (
                    DorarEnglishHadithAdmissionError(
                        "english_hadith_provider_identity_mismatch"
                    )
                )

        if (
            self.passport.get(
                "official_eligibility"
            )
            != "VERIFIED"
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_not_verified"
            )

        runtime = self.passport.get(
            "runtime"
        )

        if not isinstance(
            runtime,
            dict,
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_runtime_missing"
            )

        if (
            runtime.get("admission")
            != "ELIGIBLE_CAPTURED_CANONICAL_ARTIFACT"
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_runtime_not_eligible"
            )

        if (
            self.manifest.get(
                "runtime_admission"
            )
            != "ELIGIBLE_CAPTURED_CANONICAL_ARTIFACT"
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_manifest_not_eligible"
            )

        if (
            self.audit.get("status")
            != "PASSED"
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_audit_not_passed"
            )

    def load_record(
        self,
    ) -> DorarEnglishHadithRecord:
        records = self.manifest.get(
            "records"
        )

        if (
            not isinstance(records, list)
            or len(records) != 1
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_manifest_record_count_invalid"
            )

        spec = records[0]

        if not isinstance(
            spec,
            dict,
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_manifest_record_invalid"
            )

        canonical_url = str(
            spec.get(
                "canonical_url",
                "",
            )
        )

        if (
            canonical_url
            != _CANONICAL_URL
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_canonical_url_invalid"
            )

        artifact_path = str(
            spec.get(
                "artifact_path",
                "",
            )
        )

        expected_sha = str(
            spec.get(
                "response_sha256",
                "",
            )
        )

        if (
            len(expected_sha) != 64
            or not all(
                char
                in "0123456789abcdef"
                for char
                in expected_sha.casefold()
            )
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_expected_hash_invalid"
            )

        path = (
            self.repo_root
            / artifact_path
        ).resolve()

        try:
            path.relative_to(
                self.repo_root
            )
        except ValueError as exc:
            raise (
                DorarEnglishHadithAdmissionError(
                    "english_hadith_artifact_outside_repo"
                )
            ) from exc

        body = path.read_bytes()

        actual_sha = sha256(
            body
        ).hexdigest()

        if actual_sha != expected_sha:
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_artifact_hash_mismatch"
            )

        record = _parse_record(
            body=body,
            canonical_url=canonical_url,
            response_sha256=actual_sha,
        )

        if (
            record.hadith_number
            != str(
                spec.get(
                    "hadith_number",
                    "",
                )
            )
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_number_mismatch"
            )

        if (
            record.collection_heading
            != spec.get(
                "source_authored_collection_heading"
            )
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_heading_mismatch"
            )

        if (
            record.canonical_collection
            != spec.get(
                "canonical_collection"
            )
        ):
            raise DorarEnglishHadithAdmissionError(
                "english_hadith_collection_mismatch"
            )

        return record


class DorarEnglishHadithEvidenceAdapter:
    """
    Source-native English Hadith evidence.

    Search results are locator-only.
    Runtime answer-bearing content comes only from the
    exact SHA256-bound canonical Dorar article.

    No machine translation.
    No fuzzy Arabic/English identity join.
    No search-rank authenticity inference.
    """

    def __init__(
        self,
        *,
        repo_root: Path | str,
        policy: OfficialHadithPolicy | None = None,
    ) -> None:
        self._gate = (
            DorarEnglishHadithRuntimeGate(
                repo_root=repo_root,
            )
        )

        self._policy = (
            policy
            or OfficialHadithPolicy()
        )

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if (
            request.official_domain
            is not OfficialDomain.HADITH
        ):
            return ()

        if request.limit <= 0:
            return ()

        record = (
            self._gate.load_record()
        )

        if not _query_matches(
            query=request.query,
            hadith_text=(
                record.hadith_text
            ),
        ):
            return ()

        candidate = _PolicyCandidate(
            hadith_text=(
                record.hadith_text
            ),
            claimed_collection=(
                record.canonical_collection
            ),
            collection_reference=(
                record.canonical_url
            ),
            governed_canonical_source=True,
        )

        assessment = (
            self._policy.assess(  # type: ignore[arg-type]
                candidate
            )
        )

        if (
            assessment.decision
            is not HadithEvidenceDecision.USABLE
        ):
            return ()

        if (
            assessment.verification_state
            is not HadithVerificationState
            .SAHIHAIN_SOURCE_VERIFIED
        ):
            return ()

        base = sha256(
            (
                record.canonical_url
                + "\n"
                + record.hadith_number
                + "\n"
                + record.hadith_text
            ).encode(
                "utf-8"
            )
        ).hexdigest()[:24]

        text_id = (
            f"dorar-hadith-en:"
            f"{base}:text"
        )

        grade_id = (
            f"dorar-hadith-en:"
            f"{base}:source-verification"
        )

        text_node = EvidenceNode(
            evidence_id=text_id,
            domain=EvidenceDomain.HADITH,
            text=record.hadith_text,
            source_id=EVIDENCE_SOURCE_ID,
            source_version=(
                "dorar-en-captured-2026-10-07"
            ),
            reference=(
                record.canonical_url
            ),
            source_url=(
                record.canonical_url
            ),
            work_title=(
                record.canonical_collection
            ),
            institution=PROVIDER,
            claim_type="hadith_text",
            authority_scope=(
                "canonical_sahihain"
            ),
        )

        # This is NOT an invented muhaddith verdict.
        #
        # It is the existing OfficialHadithPolicy's
        # SAHIHAIN_SOURCE_VERIFIED state encoded into
        # the authenticity-evidence lane so the public
        # requirement can distinguish a governed
        # canonical Sahihain source from an ungraded
        # generic Hadith text.
        verification_node = EvidenceNode(
            evidence_id=grade_id,
            domain=EvidenceDomain.HADITH,
            text=(
                "Canonical Sahih al-Bukhari "
                "source verified"
            ),
            source_id=EVIDENCE_SOURCE_ID,
            source_version=(
                "dorar-en-captured-2026-10-07"
            ),
            reference=(
                record.canonical_url
            ),
            source_url=(
                record.canonical_url
            ),
            work_title=(
                record.canonical_collection
            ),
            institution=PROVIDER,
            claim_type="hadith_grade",
            topic="sahih",
            authority_scope=(
                "canonical_sahihain"
            ),
            related_hadith=(
                text_id,
            ),
        )

        return (
            text_node,
            verification_node,
        )[: request.limit]


def _contains_arabic(
    value: str,
) -> bool:
    return bool(
        re.search(
            r"[\u0600-\u06ff]",
            value,
        )
    )


def _contains_latin(
    value: str,
) -> bool:
    return bool(
        re.search(
            r"[A-Za-z]",
            value,
        )
    )


class LanguageAwareHadithEvidenceAdapter:
    """
    Language changes the presentation/retrieval surface,
    never the religious authority contract.

    Arabic -> existing Dorar Arabic lane.
    English -> governed source-native Dorar English lane.
    Mixed-script input -> existing Arabic lane, which
    preserves the previous conservative behaviour.
    """

    def __init__(
        self,
        *,
        arabic_adapter: _EvidenceAdapter,
        english_adapter: _EvidenceAdapter,
    ) -> None:
        self._arabic_adapter = (
            arabic_adapter
        )

        self._english_adapter = (
            english_adapter
        )

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if _contains_arabic(
            request.query
        ):
            return (
                self._arabic_adapter
                .retrieve(request)
            )

        if _contains_latin(
            request.query
        ):
            return (
                self._english_adapter
                .retrieve(request)
            )

        return ()
