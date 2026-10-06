from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _required_text(
    value: object,
    *,
    field_name: str,
) -> str:
    text = str(value or "").strip()

    if not text:
        raise ValueError(f"{field_name} must not be blank")

    return text


def _sha256(
    value: object,
    *,
    field_name: str,
) -> str:
    text = _required_text(
        value,
        field_name=field_name,
    ).lower()

    if not _SHA256_RE.fullmatch(text):
        raise ValueError(f"{field_name} must be SHA-256")

    return text


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaGoldUnit:
    """
    One acceptable structural location for an issue.

    A gold unit is intentionally broader than one
    passage. Many valid evidence spans may belong to
    the same fiqh chapter.

    This is retrieval relevance only. It does not
    assert that the chapter semantically supports a
    later generated claim.
    """

    book_id: str
    parent_text: str
    structural_parent_id: str | None = None
    madhhab: str | None = None
    passage_ids: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "book_id",
            _required_text(
                self.book_id,
                field_name="book_id",
            ),
        )

        object.__setattr__(
            self,
            "parent_text",
            _required_text(
                self.parent_text,
                field_name="parent_text",
            ),
        )

        if self.madhhab is not None:
            object.__setattr__(
                self,
                "madhhab",
                _required_text(
                    self.madhhab,
                    field_name="madhhab",
                ),
            )

        normalized_ids = tuple(
            dict.fromkeys(
                _required_text(
                    value,
                    field_name="passage_id",
                )
                for value in self.passage_ids
            )
        )

        object.__setattr__(
            self,
            "passage_ids",
            normalized_ids,
        )

    @property
    def key(
        self,
    ) -> tuple[
        str,
        str,
        str | None,
    ]:
        return (
            self.book_id,
            (self.structural_parent_id or self.parent_text),
            self.madhhab,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaRetrievalCase:
    case_id: str
    question: str

    gold_units: tuple[
        ShamelaGoldUnit,
        ...,
    ]

    k_values: tuple[
        int,
        ...,
    ] = (
        1,
        5,
        10,
        50,
    )

    tags: tuple[
        str,
        ...,
    ] = ()

    notes: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _required_text(
            self.case_id,
            field_name="case_id",
        )

        _required_text(
            self.question,
            field_name="question",
        )

        if not self.gold_units:
            raise ValueError(f"{self.case_id}: gold_units must not be empty")

        if tuple(sorted(set(self.k_values))) != self.k_values:
            raise ValueError(f"{self.case_id}: k_values must be unique and sorted")

        if any(value <= 0 for value in self.k_values):
            raise ValueError(f"{self.case_id}: k_values must be positive")

        keys = tuple(unit.key for unit in self.gold_units)

        if len(set(keys)) != len(keys):
            raise ValueError(f"{self.case_id}: duplicate gold structural unit")


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaRetrievalBenchmark:
    schema_version: int

    benchmark_id: str
    split: str
    description: str

    corpus_fingerprint: str
    index_fingerprint: str

    cases: tuple[
        ShamelaRetrievalCase,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaCaseMetrics:
    case_id: str
    question: str

    tags: tuple[
        str,
        ...,
    ]

    retrieved_count: int
    gold_unit_count: int
    gold_passage_count: int

    first_relevant_rank: int | None
    reciprocal_rank: float

    hit_at_k: dict[
        int,
        bool,
    ]

    parent_recall_at_k: dict[
        int,
        float,
    ]

    book_recall_at_k: dict[
        int,
        float,
    ]

    madhhab_coverage_at_k: dict[
        int,
        float | None,
    ]

    passage_recall_at_k: dict[
        int,
        float | None,
    ]

    ndcg_at_k: dict[
        int,
        float,
    ]

    context_recovery_at_k: dict[
        int,
        float,
    ]

    latency_ms: float


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaRetrievalSummary:
    case_count: int

    mean_reciprocal_rank: float

    hit_rate_at_k: dict[
        int,
        float,
    ]

    mean_parent_recall_at_k: dict[
        int,
        float,
    ]

    mean_book_recall_at_k: dict[
        int,
        float,
    ]

    mean_madhhab_coverage_at_k: dict[
        int,
        float | None,
    ]

    mean_passage_recall_at_k: dict[
        int,
        float | None,
    ]

    mean_ndcg_at_k: dict[
        int,
        float,
    ]

    mean_context_recovery_at_k: dict[
        int,
        float,
    ]

    mean_latency_ms: float
    p95_latency_ms: float


def _passage(
    hit: object,
) -> object:
    return getattr(
        hit,
        "passage",
        hit,
    )


def _metadata(
    hit: object,
) -> dict:
    passage = _passage(hit)

    value = getattr(
        passage,
        "metadata",
        None,
    )

    if isinstance(
        value,
        dict,
    ):
        return value

    if value is None:
        return {}

    return dict(value)


def _passage_id(
    hit: object,
) -> str | None:
    passage = _passage(hit)

    value = getattr(
        passage,
        "passage_id",
        None,
    )

    if value is None:
        value = getattr(
            passage,
            "evidence_id",
            None,
        )

    if value is None:
        return None

    return str(value)


def _book_id(
    hit: object,
) -> str | None:
    passage = _passage(hit)

    value = getattr(
        passage,
        "work_id",
        None,
    )

    if value is None:
        value = _metadata(hit).get("shamela_book_id")

    if value is None:
        return None

    return str(value)


def _madhhab(
    hit: object,
) -> str | None:
    value = _metadata(hit).get("madhhab")

    if value is None:
        return None

    return str(value)


def _parent_id(
    hit: object,
) -> str | None:
    value = _metadata(hit).get("structural_parent_id")

    if value is None:
        return None

    return str(value)


def _parent_text(
    hit: object,
) -> str | None:
    value = _metadata(hit).get("parent_text")

    if value is None:
        return None

    return str(value)


def _matches_unit(
    hit: object,
    unit: ShamelaGoldUnit,
) -> bool:
    if _book_id(hit) != unit.book_id:
        return False

    if unit.structural_parent_id is not None:
        if _parent_id(hit) != unit.structural_parent_id:
            return False
    elif unit.structural_parent_id is not None:
        if _parent_id(hit) != unit.structural_parent_id:
            return False
    elif _parent_text(hit) != unit.parent_text:
        return False

    if unit.madhhab is not None and _madhhab(hit) != unit.madhhab:
        return False

    return True


def _matched_units(
    gold_units: Sequence[ShamelaGoldUnit],
    hits: Sequence[object],
) -> set[
    tuple[
        str,
        str,
        str | None,
    ]
]:
    matched = set()

    for hit in hits:
        for unit in gold_units:
            if _matches_unit(
                hit,
                unit,
            ):
                matched.add(unit.key)

    return matched


def _first_relevant_rank(
    case: ShamelaRetrievalCase,
    hits: Sequence[object],
) -> int | None:
    for rank, hit in enumerate(
        hits,
        start=1,
    ):
        if any(
            _matches_unit(
                hit,
                unit,
            )
            for unit in case.gold_units
        ):
            return rank

    return None


def _ndcg(
    case: ShamelaRetrievalCase,
    hits: Sequence[object],
    *,
    k: int,
) -> float:
    """
    One gain per distinct gold structural unit.

    Repeated passages from the same chapter therefore
    do not hide failure to retrieve the second madhhab
    or second relevant chapter.
    """

    seen_units = set()

    dcg = 0.0

    for rank, hit in enumerate(
        hits[:k],
        start=1,
    ):
        matched_key = None

        for unit in case.gold_units:
            if unit.key in seen_units:
                continue

            if _matches_unit(
                hit,
                unit,
            ):
                matched_key = unit.key
                break

        if matched_key is None:
            continue

        seen_units.add(matched_key)

        dcg += 1.0 / math.log2(rank + 1)

    ideal_count = min(
        len(case.gold_units),
        k,
    )

    if ideal_count == 0:
        return 0.0

    ideal = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(
            1,
            ideal_count + 1,
        )
    )

    return dcg / ideal


def _context_recovery(
    case: ShamelaRetrievalCase,
    hits: Sequence[object],
    *,
    k: int,
) -> float:
    """
    Structural provenance recovery, not semantic
    support.

    A gold unit counts as context-recovered when a
    matching hit retains its governed parent identity,
    structural parent ID, source locator, and raw-text
    hash.
    """

    recovered = set()

    for hit in hits[:k]:
        metadata = _metadata(hit)

        if not (
            metadata.get("structural_parent_id")
            and metadata.get("source_locator")
            and metadata.get("raw_text_sha256")
        ):
            continue

        for unit in case.gold_units:
            if _matches_unit(
                hit,
                unit,
            ):
                recovered.add(unit.key)

    return len(recovered) / len(case.gold_units)


def evaluate_shamela_case(
    case: ShamelaRetrievalCase,
    hits: Sequence[object],
    *,
    latency_ms: float,
) -> ShamelaCaseMetrics:
    first_rank = _first_relevant_rank(
        case,
        hits,
    )

    gold_books = {unit.book_id for unit in case.gold_units}

    gold_madhhabs = {unit.madhhab for unit in case.gold_units if unit.madhhab}

    gold_passage_ids = {
        passage_id for unit in case.gold_units for passage_id in unit.passage_ids
    }

    hit_at_k = {}
    parent_recall_at_k = {}
    book_recall_at_k = {}
    madhhab_coverage_at_k = {}
    passage_recall_at_k = {}
    ndcg_at_k = {}
    context_recovery_at_k = {}

    for k in case.k_values:
        top = tuple(hits[:k])

        matched_units = _matched_units(
            case.gold_units,
            top,
        )

        hit_at_k[k] = bool(matched_units)

        parent_recall_at_k[k] = len(matched_units) / len(case.gold_units)

        retrieved_books = {value for hit in top if (value := _book_id(hit))}

        book_recall_at_k[k] = len(gold_books & retrieved_books) / len(gold_books)

        if gold_madhhabs:
            retrieved_madhhabs = {value for hit in top if (value := _madhhab(hit))}

            madhhab_coverage_at_k[k] = len(gold_madhhabs & retrieved_madhhabs) / len(
                gold_madhhabs
            )
        else:
            madhhab_coverage_at_k[k] = None

        if gold_passage_ids:
            retrieved_passage_ids = {
                value for hit in top if (value := _passage_id(hit))
            }

            passage_recall_at_k[k] = len(
                gold_passage_ids & retrieved_passage_ids
            ) / len(gold_passage_ids)
        else:
            passage_recall_at_k[k] = None

        ndcg_at_k[k] = _ndcg(
            case,
            hits,
            k=k,
        )

        context_recovery_at_k[k] = _context_recovery(
            case,
            hits,
            k=k,
        )

    return ShamelaCaseMetrics(
        case_id=case.case_id,
        question=case.question,
        tags=case.tags,
        retrieved_count=len(hits),
        gold_unit_count=len(case.gold_units),
        gold_passage_count=len(gold_passage_ids),
        first_relevant_rank=(first_rank),
        reciprocal_rank=(0.0 if first_rank is None else 1.0 / first_rank),
        hit_at_k=hit_at_k,
        parent_recall_at_k=(parent_recall_at_k),
        book_recall_at_k=(book_recall_at_k),
        madhhab_coverage_at_k=(madhhab_coverage_at_k),
        passage_recall_at_k=(passage_recall_at_k),
        ndcg_at_k=ndcg_at_k,
        context_recovery_at_k=(context_recovery_at_k),
        latency_ms=latency_ms,
    )


def _mean_optional(
    values: Sequence[float | None],
) -> float | None:
    present = tuple(value for value in values if value is not None)

    if not present:
        return None

    return fmean(present)


def _p95(
    values: Sequence[float],
) -> float:
    ordered = sorted(values)

    index = max(
        0,
        math.ceil(0.95 * len(ordered)) - 1,
    )

    return ordered[index]


def evaluate_shamela_suite(
    results: Sequence[ShamelaCaseMetrics],
) -> ShamelaRetrievalSummary:
    if not results:
        raise ValueError("At least one result is required")

    k_values = tuple(results[0].hit_at_k.keys())

    for result in results[1:]:
        if tuple(result.hit_at_k.keys()) != k_values:
            raise ValueError("All cases must use the same k values")

    return ShamelaRetrievalSummary(
        case_count=len(results),
        mean_reciprocal_rank=fmean(result.reciprocal_rank for result in results),
        hit_rate_at_k={
            k: fmean(float(result.hit_at_k[k]) for result in results) for k in k_values
        },
        mean_parent_recall_at_k={
            k: fmean(result.parent_recall_at_k[k] for result in results)
            for k in k_values
        },
        mean_book_recall_at_k={
            k: fmean(result.book_recall_at_k[k] for result in results) for k in k_values
        },
        mean_madhhab_coverage_at_k={
            k: _mean_optional(
                tuple(result.madhhab_coverage_at_k[k] for result in results)
            )
            for k in k_values
        },
        mean_passage_recall_at_k={
            k: _mean_optional(
                tuple(result.passage_recall_at_k[k] for result in results)
            )
            for k in k_values
        },
        mean_ndcg_at_k={
            k: fmean(result.ndcg_at_k[k] for result in results) for k in k_values
        },
        mean_context_recovery_at_k={
            k: fmean(result.context_recovery_at_k[k] for result in results)
            for k in k_values
        },
        mean_latency_ms=fmean(result.latency_ms for result in results),
        p95_latency_ms=_p95(tuple(result.latency_ms for result in results)),
    )


def load_shamela_benchmark(
    path: Path,
) -> ShamelaRetrievalBenchmark:
    document = json.loads(Path(path).read_text(encoding="utf-8"))

    if not isinstance(
        document,
        dict,
    ):
        raise ValueError("Benchmark document must be an object")

    schema_version = int(
        document.get(
            "schema_version",
            0,
        )
    )

    if schema_version != 1:
        raise ValueError("Unsupported Shamela benchmark schema version")

    root_k = tuple(
        int(value)
        for value in document.get(
            "k_values",
            (
                1,
                5,
                10,
                50,
            ),
        )
    )

    raw_cases = document.get("cases")

    if not isinstance(
        raw_cases,
        list,
    ):
        raise ValueError("cases must be an array")

    cases = []

    seen_ids = set()

    for raw_case in raw_cases:
        if not isinstance(
            raw_case,
            dict,
        ):
            raise ValueError("Each case must be an object")

        case_id = _required_text(
            raw_case.get("id"),
            field_name="case id",
        )

        if case_id in seen_ids:
            raise ValueError(f"Duplicate case id: {case_id}")

        seen_ids.add(case_id)

        raw_gold = raw_case.get("gold")

        if not isinstance(
            raw_gold,
            list,
        ):
            raise ValueError(f"{case_id}: gold must be an array")

        units = []

        for item in raw_gold:
            if not isinstance(
                item,
                dict,
            ):
                raise ValueError(f"{case_id}: gold item must be an object")

            passage_ids = item.get(
                "passage_ids",
                [],
            )

            if not isinstance(
                passage_ids,
                list,
            ):
                raise ValueError(f"{case_id}: passage_ids must be an array")

            units.append(
                ShamelaGoldUnit(
                    book_id=str(
                        item.get(
                            "book_id",
                            "",
                        )
                    ),
                    parent_text=str(
                        item.get(
                            "parent_text",
                            "",
                        )
                    ),
                    structural_parent_id=(
                        None
                        if item.get("structural_parent_id") is None
                        else str(item["structural_parent_id"])
                    ),
                    madhhab=(
                        None if item.get("madhhab") is None else str(item["madhhab"])
                    ),
                    passage_ids=tuple(str(value) for value in passage_ids),
                )
            )

        case_k = tuple(
            int(value)
            for value in raw_case.get(
                "k_values",
                root_k,
            )
        )

        tags = tuple(
            str(value)
            for value in raw_case.get(
                "tags",
                (),
            )
        )

        notes = raw_case.get("notes")

        cases.append(
            ShamelaRetrievalCase(
                case_id=case_id,
                question=_required_text(
                    raw_case.get("question"),
                    field_name=(f"{case_id} question"),
                ),
                gold_units=tuple(units),
                k_values=case_k,
                tags=tags,
                notes=(None if notes is None else str(notes)),
            )
        )

    if not cases:
        raise ValueError("Benchmark has no cases")

    return ShamelaRetrievalBenchmark(
        schema_version=1,
        benchmark_id=_required_text(
            document.get("benchmark_id"),
            field_name="benchmark_id",
        ),
        split=_required_text(
            document.get("split"),
            field_name="split",
        ),
        description=_required_text(
            document.get("description"),
            field_name="description",
        ),
        corpus_fingerprint=_sha256(
            document.get("corpus_fingerprint"),
            field_name=("corpus_fingerprint"),
        ),
        index_fingerprint=_sha256(
            document.get("index_fingerprint"),
            field_name=("index_fingerprint"),
        ),
        cases=tuple(cases),
    )
