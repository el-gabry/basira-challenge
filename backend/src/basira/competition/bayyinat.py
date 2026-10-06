from __future__ import annotations

import json
import re
import unicodedata

from functools import lru_cache
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[3]


SNAPSHOT = (
    ROOT
    / "data"
    / "competition"
    / "sources"
    / "shubuhat"
    / "bayyinat_units_v1.json"
)


DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


ARABIC_STOPWORDS = {
    "في",
    "من",
    "على",
    "الي",
    "الى",
    "هل",
    "ما",
    "هو",
    "هي",
    "هذا",
    "هذه",
    "ان",
    "أن",
    "عن",
    "او",
    "أو",
    "ثم",
    "مع",
}


def normalize_arabic(
    value: str,
) -> str:

    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    value = DIACRITICS.sub(
        "",
        value,
    )

    value = value.replace(
        "ـ",
        "",
    )

    value = value.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ٱ": "ا",
                "ى": "ي",
                "ؤ": "و",
                "ئ": "ي",
            }
        )
    )

    value = re.sub(
        r"[^\w\u0600-\u06ff]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def tokens(
    value: str,
) -> set[str]:

    return {
        token
        for token in normalize_arabic(
            value
        ).split()
        if (
            len(token) >= 2
            and token
            not in ARABIC_STOPWORDS
        )
    }


@lru_cache(maxsize=1)
def load_snapshot() -> dict:

    data = json.loads(
        SNAPSHOT.read_text(
            encoding="utf-8"
        )
    )

    if (
        data["artifact"]["sha256"]
        !=
        "619b7201833419b8fbf86c463208462b9a2a7f02ad2306a2667490f3b410ad4e"
    ):
        raise RuntimeError(
            "unexpected Bayyinat snapshot artifact"
        )

    if len(
        data["units"]
    ) != 263:
        raise RuntimeError(
            "unexpected Bayyinat unit count"
        )

    return data


def get_bayyinat_unit(
    ordinal: int,
) -> dict:

    if not (
        1
        <= ordinal
        <= 263
    ):
        raise KeyError(
            ordinal
        )

    return load_snapshot()[
        "units"
    ][
        ordinal - 1
    ]


FIELD_WEIGHTS = {
    "title":
        8.0,

    "question_text":
        7.0,

    "gist":
        5.0,

    "short_answer":
        5.0,

    "keywords":
        4.0,

    "related_questions":
        3.0,

    "conclusion":
        2.0,

    "detailed_answer":
        1.0,
}


def search_bayyinat(
    query: str,
    *,
    limit: int = 5,
) -> list[dict]:

    if limit <= 0:
        return []

    normalized_query = normalize_arabic(
        query
    )

    query_tokens = tokens(
        query
    )

    if not normalized_query:
        return []


    results = []


    for unit in load_snapshot()[
        "units"
    ]:

        score = 0.0

        matched_fields = []


        for field, weight in (
            FIELD_WEIGHTS.items()
        ):

            raw_value = (
                unit.get(
                    field
                )
                or ""
            )

            if not raw_value:
                continue


            normalized_value = normalize_arabic(
                raw_value
            )

            field_tokens = tokens(
                raw_value
            )


            overlap = (
                query_tokens
                & field_tokens
            )


            if overlap:

                score += (
                    len(overlap)
                    * weight
                )

                matched_fields.append(
                    field
                )


            if (
                normalized_query
                in normalized_value
            ):

                score += (
                    weight
                    * 5.0
                )


        if score <= 0:
            continue


        results.append(
            {
                "source":
                    "BAYYINAT",

                "ordinal":
                    unit[
                        "ordinal"
                    ],

                "score":
                    round(
                        score,
                        4,
                    ),

                "matched_fields":
                    sorted(
                        set(
                            matched_fields
                        )
                    ),

                "title":
                    unit[
                        "title"
                    ],

                "question_text":
                    unit[
                        "question_text"
                    ],

                "short_answer":
                    unit[
                        "short_answer"
                    ],

                "provenance":
                    unit[
                        "provenance"
                    ],

                "source_role": {
                    "primary_conversational_source":
                        True,

                    "universal_primary_evidence":
                        False,

                    "cross_domain_primary_routing_required":
                        True,

                    "internal_citation_contract_frozen":
                        False,
                },
            }
        )


    results.sort(
        key=lambda item: (
            -item[
                "score"
            ],
            item[
                "ordinal"
            ],
        )
    )


    return results[
        :limit
    ]
# BAYYINAT_CONCEPT_COVERAGE_RERANKER_V1
#
# Competition-sufficient lexical reranking over the governed
# candidate pool.
#
# This does NOT alter:
# - source eligibility
# - unit boundaries
# - provenance
# - evidence authority
#
# It only improves ranking by rewarding coverage of the user's
# distinct concepts, with stronger weight for title/question.


_search_bayyinat_governed_base = search_bayyinat


def _bayyinat_rank_normalize(
    value: object,
) -> str:

    import re
    import unicodedata

    text = unicodedata.normalize(
        "NFKC",
        str(
            value
            or ""
        ),
    )

    text = re.sub(
        r"[\u0610-\u061a"
        r"\u064b-\u065f"
        r"\u0670"
        r"\u06d6-\u06ed]",
        "",
        text,
    )

    text = text.replace(
        "ـ",
        "",
    )

    text = text.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ٱ": "ا",
                "ؤ": "و",
                "ئ": "ي",
                "ى": "ي",
                "ة": "ه",
            }
        )
    )

    text = re.sub(
        r"[^ء-ي0-9]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


_BAYYINAT_STOPWORDS = {
    "ما",
    "ماذا",
    "متى",
    "اين",
    "كيف",
    "هل",
    "لماذا",
    "لم",
    "لن",
    "من",
    "في",
    "على",
    "عن",
    "الى",
    "مع",
    "هذا",
    "هذه",
    "ذلك",
    "تلك",
    "هو",
    "هي",
    "هم",
    "ان",
    "انه",
    "انها",
    "او",
    "ثم",
    "قد",
    "كل",
}


def _bayyinat_term(
    token: str,
) -> str:

    token = _bayyinat_rank_normalize(
        token
    )

    if not token:
        return ""


    # Strip common attached conjunction/preposition.
    #
    # Conservative: only one character and only if enough of
    # the lexical stem remains.
    if (
        len(token) >= 5
        and token[0] in "وفبكل"
    ):
        token = token[1:]


    if (
        len(token) >= 5
        and token.startswith(
            "ال"
        )
    ):
        token = token[2:]


    return token


def _bayyinat_terms(
    value: object,
) -> set[str]:

    normalized = _bayyinat_rank_normalize(
        value
    )

    output = set()


    for raw in normalized.split():

        term = _bayyinat_term(
            raw
        )

        if (
            len(term) < 3
            or term
            in _BAYYINAT_STOPWORDS
        ):
            continue

        output.add(
            term
        )


    return output


def _bayyinat_term_matches(
    query_term: str,
    candidate_term: str,
) -> bool:

    if (
        query_term
        == candidate_term
    ):
        return True


    # Arabic inflection / attached suffix tolerance.
    #
    # e.g.:
    #   اعمال <-> اعمالها
    #   كتابه <-> لكتابه after prefix normalization
    #
    if (
        min(
            len(query_term),
            len(candidate_term),
        )
        >= 4
        and
        (
            query_term.startswith(
                candidate_term
            )
            or
            candidate_term.startswith(
                query_term
            )
        )
    ):
        return True


    return False


def _bayyinat_field_terms(
    hit: dict,
    field: str,
) -> set[str]:

    return _bayyinat_terms(
        hit.get(
            field,
            ""
        )
    )


def _bayyinat_has_term(
    query_term: str,
    terms: set[str],
) -> bool:

    return any(
        _bayyinat_term_matches(
            query_term,
            candidate,
        )
        for candidate in terms
    )


def _bayyinat_rerank(
    query: str,
    hits: list[dict],
) -> list[dict]:

    import math


    q_terms = _bayyinat_terms(
        query
    )


    if not q_terms:
        return hits


    field_weights = {
        "title":
            9.0,

        "question":
            8.0,

        "canonical_question":
            8.0,

        "similar_formulations":
            5.0,

        "gist":
            4.0,

        "short_answer":
            3.0,

        "detailed_answer":
            1.0,

        "conclusion":
            2.0,

        "keywords":
            4.0,

        "related_questions":
            3.0,

        "text":
            0.75,

        "raw_text":
            0.75,

        "unit_text":
            0.75,
    }


    prepared = []


    for hit in hits:

        fields = {
            field:
                _bayyinat_field_terms(
                    hit,
                    field,
                )
            for field
            in field_weights
        }


        all_terms = set().union(
            *fields.values()
        )


        prepared.append(
            (
                hit,
                fields,
                all_terms,
            )
        )


    # Document frequency only inside the governed candidate
    # pool. Rare query concepts receive higher value.
    df = {}


    for query_term in q_terms:

        count = sum(
            _bayyinat_has_term(
                query_term,
                all_terms,
            )
            for _, _, all_terms
            in prepared
        )

        df[
            query_term
        ] = count


    n_docs = max(
        1,
        len(
            prepared
        ),
    )


    idf = {
        term:
            (
                math.log(
                    (
                        n_docs
                        + 1
                    )
                    /
                    (
                        df[
                            term
                        ]
                        + 1
                    )
                )
                + 1.0
            )
        for term in q_terms
    }


    ranked = []


    for hit, fields, all_terms in prepared:

        matched = {
            term
            for term in q_terms
            if _bayyinat_has_term(
                term,
                all_terms,
            )
        }


        coverage = (
            len(
                matched
            )
            / len(
                q_terms
            )
        )


        lexical_score = 0.0


        for query_term in q_terms:

            best_field_weight = 0.0


            for field, weight in (
                field_weights.items()
            ):

                if _bayyinat_has_term(
                    query_term,
                    fields[
                        field
                    ],
                ):

                    best_field_weight = max(
                        best_field_weight,
                        weight,
                    )


            lexical_score += (
                best_field_weight
                * idf[
                    query_term
                ]
            )


        # Strong generic reward for satisfying several distinct
        # concepts in the same unit.
        concept_bonus = (
            18.0
            * coverage
            * coverage
        )


        if len(
            matched
        ) >= 2:

            concept_bonus += (
                3.0
                * (
                    len(
                        matched
                    )
                    - 1
                )
            )


        # Preserve old score only as weak tie-break evidence.
        try:
            old_score = float(
                hit.get(
                    "score",
                    0.0,
                )
                or 0.0
            )

        except (
            TypeError,
            ValueError,
        ):
            old_score = 0.0


        final_score = (
            lexical_score
            + concept_bonus
            + (
                old_score
                * 0.05
            )
        )


        enriched = dict(
            hit
        )

        enriched[
            "score"
        ] = round(
            final_score,
            6,
        )

        enriched[
            "query_concept_coverage"
        ] = round(
            coverage,
            6,
        )


        ranked.append(
            enriched
        )


    ranked.sort(
        key=lambda item: (
            -float(
                item.get(
                    "score",
                    0.0,
                )
            ),
            int(
                item.get(
                    "ordinal",
                    10**9,
                )
            ),
        )
    )


    return ranked


def search_bayyinat(
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    Governed Bayyinat retrieval with concept-coverage reranking.

    Candidate generation remains the existing governed adapter.
    Reranking favors units covering multiple distinct query
    concepts, especially in title/question fields.
    """

    if limit <= 0:
        return []


    # Dataset contains exactly 263 governed canonical units.
    # Pull the whole governed candidate pool so early lexical
    # ranking cannot hide the best semantic lexical match.
    candidates = _search_bayyinat_governed_base(
        query,
        limit=263,
    )


    ranked = _bayyinat_rerank(
        query,
        list(
            candidates
        ),
    )


    return ranked[
        :limit
    ]
