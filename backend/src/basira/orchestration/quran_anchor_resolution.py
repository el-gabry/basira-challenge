from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from basira.normalization.quran import (
    normalize_quran_search_text,
)
from basira.orchestration.evidence_acceptance import (
    AnchorKind,
    AnchorOrigin,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.quran_canonical_resolver import (
    resolve_explicit_quran_point,
)
from basira.sources.quran.repository import (
    QuranRepository,
)

_NUMERIC_REFERENCE_RE = re.compile(
    r"(?<!\d)"
    r"(\d{1,3})"
    r"\s*:\s*"
    r"(\d{1,4})"
    r"(?!\d)"
)


_ANCHOR_SEEKING_CUES = (
    "قوله تعالى",
    "قال تعالى",
    "في قوله",
    "هذه الاية",
    "هذه الآية",
    "الاية",
    "الآية",
    "اية",
    "آية",
)


_SHORT_QURAN_EXPLANATION_PREFIXES = (
    "ما معنى قوله تعالى",
    "ما معني قوله تعالى",
    "ما تفسير قوله تعالى",
    "ما معنى قول الله تعالى",
    "ما معني قول الله تعالى",
    "ما تفسير قول الله تعالى",
    "فسر قوله تعالى",
    "فسر قول الله تعالى",
    "تفسير قوله تعالى",
    "تفسير قول الله تعالى",
    "ما معنى",
    "ما معني",
    "ما تفسير",
    "تفسير",
    "شرح",
    "فسر",
)


class AnchorResolutionDisposition(StrEnum):
    """
    Identity-resolution result only.

    NO_ANCHOR does not mean the question is
    semantically unambiguous. It means canonical
    evidence did not justify a hard identity lock.
    """

    RESOLVED = "resolved"
    NO_ANCHOR = "no_anchor"
    ASK_USER = "ask_user"
    BOUNDED_BRANCH = "bounded_branch"


@dataclass(
    frozen=True,
    slots=True,
)
class VerifiedCanonicalAnchor:
    """
    A canonical identity established without planner
    inference.

    This is deliberately not EvidenceAnchor yet.
    Claim-specific evidence domains belong to the
    later evidence-contract compiler.
    """

    reference: str
    kind: AnchorKind
    origin: AnchorOrigin

    matched_text: str | None = None

    def __post_init__(
        self,
    ) -> None:
        reference = self.reference.strip()

        if not reference:
            raise ValueError("verified anchor reference must be nonblank")

        if self.origin is AnchorOrigin.PLANNER_INFERENCE:
            raise ValueError("planner inference cannot be a verified canonical anchor")

        object.__setattr__(
            self,
            "reference",
            reference,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class QuranAnchorResolution:
    disposition: AnchorResolutionDisposition

    anchors: tuple[
        VerifiedCanonicalAnchor,
        ...,
    ] = ()

    candidate_references: tuple[
        str,
        ...,
    ] = ()

    reason: str = ""

    def __post_init__(
        self,
    ) -> None:
        if (
            self.disposition is AnchorResolutionDisposition.RESOLVED
            and not self.anchors
        ):
            raise ValueError("resolved anchor result must contain an anchor")

        if (
            self.disposition
            in {
                AnchorResolutionDisposition.ASK_USER,
                AnchorResolutionDisposition.BOUNDED_BRANCH,
            }
            and self.anchors
        ):
            raise ValueError(
                "ambiguous anchor result cannot contain a hard verified anchor"
            )

        if self.disposition is AnchorResolutionDisposition.NO_ANCHOR and self.anchors:
            raise ValueError("no-anchor result cannot contain anchors")


@dataclass(
    frozen=True,
    slots=True,
)
class _CanonicalPhraseMatch:
    references: tuple[
        str,
        ...,
    ]

    matched_text: str | None


def _reference_sort_key(
    reference: str,
) -> tuple[
    int,
    int,
]:
    surah, ayah = reference.split(
        ":",
        maxsplit=1,
    )

    return (
        int(surah),
        int(ayah),
    )


class QuranCanonicalAnchorResolver:
    """
    Resolve Quran identity only from deterministic,
    canonical evidence.

    Allowed HARD-quality origins:
    - explicit numeric Quran reference verified
      against QuranRepository;
    - unique canonical Quran text match.

    This component does not:
    - infer religious meaning;
    - create ClaimTask;
    - choose source authority;
    - perform answer generation;
    - promote planner guesses.
    """

    def __init__(
        self,
        *,
        repository: QuranRepository,
        min_canonical_tokens: int = 4,
    ) -> None:
        if min_canonical_tokens < 3:
            raise ValueError("min_canonical_tokens must be >= 3")

        self._repository = repository

        self._min_canonical_tokens = min_canonical_tokens

    @staticmethod
    def _explicit_reference(
        understanding: (BasiraQueryUnderstanding),
    ) -> str | None:
        match = _NUMERIC_REFERENCE_RE.search(understanding.query.original_text)

        if match is None:
            return None

        return f"{int(match.group(1))}:{int(match.group(2))}"

    @staticmethod
    def _is_anchor_seeking(
        understanding: (BasiraQueryUnderstanding),
    ) -> bool:
        text = understanding.query.original_text

        return any(cue in text for cue in _ANCHOR_SEEKING_CUES)

    def _canonical_phrase_match(
        self,
        understanding: (BasiraQueryUnderstanding),
    ) -> _CanonicalPhraseMatch:
        normalized = normalize_quran_search_text(understanding.query.original_text)

        tokens = tuple(token for token in normalized.split() if token)

        if len(tokens) < self._min_canonical_tokens:
            return _CanonicalPhraseMatch(
                references=(),
                matched_text=None,
            )

        for size in range(
            len(tokens),
            self._min_canonical_tokens - 1,
            -1,
        ):
            reference_to_phrases: dict[
                str,
                set[str],
            ] = {}

            for start in range(
                0,
                len(tokens) - size + 1,
            ):
                phrase = " ".join(tokens[start : start + size])

                matches = self._repository.find_containing(phrase)

                for verse in matches:
                    reference_to_phrases.setdefault(
                        verse.reference,
                        set(),
                    ).add(phrase)

            if not reference_to_phrases:
                continue

            references = tuple(
                sorted(
                    reference_to_phrases,
                    key=(_reference_sort_key),
                )
            )

            phrases = {
                phrase for values in reference_to_phrases.values() for phrase in values
            }

            matched_text = max(
                phrases,
                key=lambda value: (
                    len(value.split()),
                    len(value),
                    value,
                ),
            )

            return _CanonicalPhraseMatch(
                references=references,
                matched_text=matched_text,
            )

        return _CanonicalPhraseMatch(
            references=(),
            matched_text=None,
        )

    def _short_canonical_phrase_match(
        self,
        understanding: BasiraQueryUnderstanding,
    ) -> _CanonicalPhraseMatch:
        """
        Identity-only probe for a short quoted fragment.

        Two or three canonical tokens are allowed only
        after a bounded explanation prefix. This never
        creates religious evidence or source authority.
        """
        normalized = normalize_quran_search_text(
            understanding.query.original_text
        )

        prefixes = sorted(
            (
                normalize_quran_search_text(
                    prefix
                )
                for prefix
                in _SHORT_QURAN_EXPLANATION_PREFIXES
            ),
            key=lambda value: (
                len(value.split()),
                len(value),
            ),
            reverse=True,
        )

        candidate = None

        for prefix in prefixes:
            marker = f"{prefix} "

            if normalized.startswith(
                marker
            ):
                candidate = normalized[
                    len(marker):
                ].strip()

                break

        if not candidate:
            return _CanonicalPhraseMatch(
                references=(),
                matched_text=None,
            )

        tokens = tuple(
            token
            for token in candidate.split()
            if token
        )

        if not 2 <= len(tokens) <= 3:
            return _CanonicalPhraseMatch(
                references=(),
                matched_text=None,
            )

        matches = (
            self._repository
            .find_containing(
                candidate
            )
        )

        references = tuple(
            sorted(
                {
                    verse.reference
                    for verse in matches
                },
                key=_reference_sort_key,
            )
        )

        return _CanonicalPhraseMatch(
            references=references,
            matched_text=candidate,
        )

    def resolve(
        self,
        understanding: (BasiraQueryUnderstanding),
    ) -> QuranAnchorResolution:
        explicit = self._explicit_reference(understanding)

        # Numeric references keep their existing behavior,
        # including invalid-reference and conflict handling.
        #
        # If no numeric reference exists, allow the shared
        # explicit Quran identity resolver to recognize
        # deterministic Surah-name + ayah wording.
        #
        # This does NOT use partial-text discovery and does
        # NOT grant evidence authority. The resulting
        # canonical coordinate still passes through the
        # existing repository validation and conflict
        # firewall below.
        if explicit is None:
            explicit_point = resolve_explicit_quran_point(
                question=(
                    understanding.query.original_text
                ),
                repository=self._repository,
            )

            if explicit_point is not None:
                explicit = explicit_point.reference

        phrase_match = self._canonical_phrase_match(understanding)

        if explicit is not None:
            surah, ayah = explicit.split(
                ":",
                maxsplit=1,
            )

            verse = self._repository.get(
                int(surah),
                int(ayah),
            )

            if verse is None:
                return QuranAnchorResolution(
                    disposition=(AnchorResolutionDisposition.ASK_USER),
                    candidate_references=(phrase_match.references),
                    reason=("explicit_quran_reference_not_found"),
                )

            if (
                len(phrase_match.references) == 1
                and phrase_match.references[0] != explicit
            ):
                return QuranAnchorResolution(
                    disposition=(AnchorResolutionDisposition.ASK_USER),
                    candidate_references=(
                        tuple(
                            dict.fromkeys(
                                (
                                    explicit,
                                    *phrase_match.references,
                                )
                            )
                        )
                    ),
                    reason=("explicit_reference_conflicts_with_canonical_text"),
                )

            if (
                len(phrase_match.references) > 1
                and explicit not in phrase_match.references
            ):
                return QuranAnchorResolution(
                    disposition=(AnchorResolutionDisposition.ASK_USER),
                    candidate_references=(
                        tuple(
                            dict.fromkeys(
                                (
                                    explicit,
                                    *phrase_match.references,
                                )
                            )
                        )
                    ),
                    reason=("explicit_reference_conflicts_with_canonical_candidates"),
                )

            return QuranAnchorResolution(
                disposition=(AnchorResolutionDisposition.RESOLVED),
                anchors=(
                    VerifiedCanonicalAnchor(
                        reference=explicit,
                        kind=(AnchorKind.QURAN_AYAH),
                        origin=(AnchorOrigin.EXPLICIT_REFERENCE),
                        matched_text=(phrase_match.matched_text),
                    ),
                ),
                reason=("verified_explicit_quran_reference"),
            )

        if not phrase_match.references:
            short_match = (
                self._short_canonical_phrase_match(
                    understanding
                )
            )

            if len(
                short_match.references
            ) > 1:
                return QuranAnchorResolution(
                    disposition=(
                        AnchorResolutionDisposition
                        .BOUNDED_BRANCH
                    ),
                    candidate_references=(
                        short_match.references
                    ),
                    reason=(
                        "short_canonical_text_matches_"
                        "multiple_quran_verses"
                    ),
                )

            if len(
                short_match.references
            ) == 1:
                if self._is_anchor_seeking(
                    understanding
                ):
                    return QuranAnchorResolution(
                        disposition=(
                            AnchorResolutionDisposition
                            .RESOLVED
                        ),
                        anchors=(
                            VerifiedCanonicalAnchor(
                                reference=(
                                    short_match
                                    .references[0]
                                ),
                                kind=(
                                    AnchorKind.QURAN_AYAH
                                ),
                                origin=(
                                    AnchorOrigin
                                    .CANONICAL_TEXT_MATCH
                                ),
                                matched_text=(
                                    short_match
                                    .matched_text
                                ),
                            ),
                        ),
                        reason=(
                            "unique_short_canonical_"
                            "quran_text_match"
                        ),
                    )

                # A unique two/three-token coincidence
                # still cannot silently become a HARD
                # Quran identity.
                return QuranAnchorResolution(
                    disposition=(
                        AnchorResolutionDisposition
                        .ASK_USER
                    ),
                    candidate_references=(
                        short_match.references
                    ),
                    reason=(
                        "short_quran_text_match_"
                        "requires_confirmation"
                    ),
                )

        if len(phrase_match.references) == 1:
            return QuranAnchorResolution(
                disposition=(AnchorResolutionDisposition.RESOLVED),
                anchors=(
                    VerifiedCanonicalAnchor(
                        reference=(phrase_match.references[0]),
                        kind=(AnchorKind.QURAN_AYAH),
                        origin=(AnchorOrigin.CANONICAL_TEXT_MATCH),
                        matched_text=(phrase_match.matched_text),
                    ),
                ),
                reason=("unique_canonical_quran_text_match"),
            )

        if len(phrase_match.references) > 1:
            return QuranAnchorResolution(
                disposition=(AnchorResolutionDisposition.BOUNDED_BRANCH),
                candidate_references=(phrase_match.references),
                reason=("canonical_text_matches_multiple_quran_verses"),
            )

        if self._is_anchor_seeking(understanding):
            return QuranAnchorResolution(
                disposition=(AnchorResolutionDisposition.ASK_USER),
                reason=("anchor_requested_but_not_canonically_resolved"),
            )

        return QuranAnchorResolution(
            disposition=(AnchorResolutionDisposition.NO_ANCHOR),
            reason=("no_verified_quran_anchor"),
        )
