from __future__ import annotations

import re
import unicodedata
from hashlib import sha256
from typing import Protocol

from basira.competition.dorar_fiqh import (
    DorarFiqhArticle,
    parse_dorar_fiqh_article,
)
from basira.competition.dorar_fiqh_admission import (
    DorarFiqhRuntimeAdmission,
    DorarFiqhRuntimeGate,
)
from basira.competition.dorar_fiqh_source import (
    DorarFiqhSourceClient,
    DorarFiqhSourceError,
    DorarFiqhSourceSearchResult,
)
from basira.competition.dorar_transport import (
    DorarTransportError,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
    CompetitionSourceUnavailable,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)

_GENERIC_FIQH_RELEVANCE_TERMS = frozenset(
    {
        "ما",
        "ماذا",
        "هل",
        "وهل",
        "حكم",
        "الحكم",
        "ماحكم",
        "ينقض",
        "تنقض",
        "ينقضه",
        "الوضوء",
        "وضوء",
        "المطلب",
        "الباب",
        "الفصل",
        "المسالة",
        "المسألة",
        "الاول",
        "الثاني",
        "الثالث",
        "الرابع",
        "الخامس",
        "السادس",
        "السابع",
        "الثامن",
        "التاسع",
        "العاشر",
        "الموسوعة",
        "الفقهية",
        "الدرر",
        "السنية",
    }
)


def _normalize_relevance_text(
    value: str,
) -> str:
    value = "".join(
        character
        for character in unicodedata.normalize(
            "NFKD",
            value,
        )
        if unicodedata.category(
            character
        )
        != "Mn"
    )

    value = value.replace(
        "ـ",
        "",
    )

    for source in (
        "أ",
        "إ",
        "آ",
        "ٱ",
    ):
        value = value.replace(
            source,
            "ا",
        )

    value = value.replace(
        "ى",
        "ي",
    )

    value = re.sub(
        r"[^\u0621-\u063a"
        r"\u0641-\u064a0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def _relevance_terms(
    value: str,
) -> tuple[str, ...]:
    normalized = (
        _normalize_relevance_text(
            value
        )
    )

    return tuple(
        token
        for token in normalized.split()
        if (
            len(token) > 1
            and token
            not in (
                _GENERIC_FIQH_RELEVANCE_TERMS
            )
        )
    )


def _article_relevance_score(
    *,
    query: str,
    article: DorarFiqhArticle,
) -> int:
    """
    Deterministic issue-level relevance admission.

    Search may broaden.
    Evidence returned to reasoning must narrow.

    Only canonical article-title structure may
    establish issue relevance here. Article body
    text is deliberately NOT used to rescue an
    unrelated search candidate.
    """

    if not article.article_title:
        return 0

    query_terms = _relevance_terms(
        query
    )

    title_terms = _relevance_terms(
        article.article_title
    )

    if (
        not query_terms
        or not title_terms
    ):
        return 0

    query_set = set(
        query_terms
    )

    title_set = set(
        title_terms
    )

    token_overlap = len(
        query_set
        & title_set
    )

    query_bigrams = set(
        zip(
            query_terms,
            query_terms[1:],
            strict=False,
        )
    )

    title_bigrams = set(
        zip(
            title_terms,
            title_terms[1:],
            strict=False,
        )
    )

    phrase_overlap = len(
        query_bigrams
        & title_bigrams
    )

    return (
        token_overlap
        + (2 * phrase_overlap)
    )


class DorarFiqhClientProtocol(
    Protocol
):
    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> DorarFiqhSourceSearchResult: ...


def _scope_value(
    value: object,
) -> str:
    raw = getattr(
        value,
        "value",
        value,
    )

    return str(raw)


def _stable_id(
    *parts: str,
) -> str:
    digest = sha256()

    for part in parts:
        digest.update(
            part.encode("utf-8")
        )
        digest.update(b"\0")

    return (
        "dorar-fiqh:"
        + digest.hexdigest()[:24]
    )


def _explicit_disagreement_marker(
    article: DorarFiqhArticle,
) -> str | None:
    if not article.explicit_disagreement:
        return None

    for marker in (
        "اختلف أهل العلم",
        "اختلف أهلُ العِلم",
        "على قولين",
        "على ثلاثة أقوال",
        "على أقوال",
    ):
        if marker in article.full_text:
            return marker

    # Parser says explicit disagreement but the
    # recognized literal marker is not recoverable.
    # Fail narrow: do not manufacture text.
    return None


class DorarFiqhEvidenceAdapter:
    """
    Governed Dorar Fiqh evidence lane.

    Discovery does not create evidence.

    Only:
      canonical Dorar article
      -> runtime admission
      -> real Dorar parser
      -> exact attributed position text
      -> EvidenceNode

    No tarjih, majority vote, consensus inference,
    or personal fatwa is performed here.
    """

    def __init__(
        self,
        *,
        client: (
            DorarFiqhClientProtocol
            | DorarFiqhSourceClient
        ),
        gate: DorarFiqhRuntimeGate,
    ) -> None:
        self.client = client
        self.gate = gate

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if (
            request.official_domain
            is not OfficialDomain.GENERAL_FIQH
        ):
            raise ValueError(
                "DorarFiqhEvidenceAdapter requires "
                "GENERAL_FIQH."
            )

        query = request.query.strip()

        if not query or request.limit <= 0:
            return ()

        try:
            result = self.client.search(
                query,
                limit=request.limit,
            )
        except (
            DorarFiqhSourceError,
            DorarTransportError,
        ) as exc:
            raise CompetitionSourceUnavailable(
                "dorar_fiqh"
            ) from exc

        parsed_candidates: list[
            tuple[
                int,
                DorarFiqhArticle,
                DorarFiqhRuntimeAdmission,
            ]
        ] = []

        for document in result.documents:
            try:
                admission = self.gate.admit(
                    document
                )

                body = document.body

                html = (
                    body.decode(
                        "utf-8",
                        errors="strict",
                    )
                    if isinstance(
                        body,
                        bytes,
                    )
                    else str(body)
                )

                article = (
                    parse_dorar_fiqh_article(
                        html=html,
                        canonical_url=(
                            document
                            .canonical_url
                        ),
                    )
                )
            except (
                UnicodeDecodeError,
                ValueError,
            ):
                # Candidate-local failure.
                # Never promote raw/unparseable
                # material into evidence.
                continue

            relevance_score = (
                _article_relevance_score(
                    query=query,
                    article=article,
                )
            )

            if relevance_score <= 0:
                continue

            parsed_candidates.append(
                (
                    relevance_score,
                    article,
                    admission,
                )
            )

        if not parsed_candidates:
            return ()

        best_score = max(
            score
            for (
                score,
                _article,
                _admission,
            )
            in parsed_candidates
        )

        evidence: list[
            EvidenceNode
        ] = []

        seen: set[str] = set()

        for (
            relevance_score,
            article,
            admission,
        ) in parsed_candidates:
            if (
                relevance_score
                != best_score
            ):
                continue

            nodes = self._article_nodes(
                article=article,
                admission=admission,
            )

            for node in nodes:
                if (
                    node.evidence_id
                    in seen
                ):
                    continue

                seen.add(
                    node.evidence_id
                )

                evidence.append(
                    node
                )

        return tuple(evidence)

    @staticmethod
    def _article_nodes(
        *,
        article: DorarFiqhArticle,
        admission: DorarFiqhRuntimeAdmission,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        # Important:
        # An article without source-authored position
        # boundaries stays unavailable as Fiqh evidence.
        #
        # We do NOT promote the whole article body merely
        # because it was retrieved.
        if not article.positions:
            return ()

        nodes: list[
            EvidenceNode
        ] = []

        root_ids: list[str] = []

        conflict_group = (
            f"fiqh:{article.source_id}"
            if (
                article.explicit_disagreement
                and len(article.positions) > 1
            )
            else None
        )

        for position in article.positions:
            text = position.text

            if (
                not text
                or text not in article.full_text
            ):
                continue

            madhhabs = (
                tuple(position.madhhabs)
                or (None,)
            )

            ordinal = str(
                position.ordinal
            )

            for madhhab in madhhabs:
                scope = (
                    _scope_value(madhhab)
                    if madhhab is not None
                    else None
                )

                evidence_id = (
                    _stable_id(
                        article.source_id,
                        ordinal,
                        scope or "unspecified",
                        text,
                    )
                    + ":position"
                )

                node = EvidenceNode(
                    evidence_id=evidence_id,
                    domain=(
                        EvidenceDomain.FIQH
                    ),
                    text=text,
                    source_id=(
                        article.source_id
                    ),
                    source_version=(
                        admission
                        .response_sha256
                    ),
                    reference=(
                        article.article_title
                    ),
                    source_url=(
                        article.canonical_url
                    ),
                    work_id="dorar-fiqh",
                    work_title=(
                        article.article_title
                    ),
                    institution=(
                        admission.provider
                    ),
                    publisher=(
                        admission.provider
                    ),
                    topic=(
                        article.article_title
                    ),
                    claim_type=(
                        "fiqh_position"
                    ),
                    authority_scope=scope,
                    related_fiqh=(
                        article.source_id,
                    ),
                    conflict_group=(
                        conflict_group
                    ),
                    conflict_type=(
                        "fiqh_position"
                        if conflict_group
                        else None
                    ),
                )

                nodes.append(node)

                root_ids.append(
                    evidence_id
                )

        marker = (
            _explicit_disagreement_marker(
                article
            )
        )

        if (
            marker is not None
            and root_ids
        ):
            nodes.append(
                EvidenceNode(
                    evidence_id=(
                        _stable_id(
                            article.source_id,
                            "disagreement",
                            marker,
                        )
                        + ":disagreement"
                    ),
                    domain=(
                        EvidenceDomain.FIQH
                    ),
                    text=marker,
                    source_id=(
                        article.source_id
                    ),
                    source_version=(
                        admission
                        .response_sha256
                    ),
                    reference=(
                        article.article_title
                    ),
                    source_url=(
                        article.canonical_url
                    ),
                    work_id="dorar-fiqh",
                    work_title=(
                        article.article_title
                    ),
                    institution=(
                        admission.provider
                    ),
                    publisher=(
                        admission.provider
                    ),
                    topic=(
                        article.article_title
                    ),
                    claim_type=(
                        "fiqh_disagreement"
                    ),
                    related_fiqh=(
                        root_ids[0],
                    ),
                    conflict_group=(
                        conflict_group
                    ),
                    conflict_type=(
                        "fiqh_position"
                    ),
                )
            )

        return tuple(nodes)
