from __future__ import annotations

from collections.abc import (
    Iterable,
)
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from basira.evidence.models import (
    EvidenceNode,
)
from basira.evidence.scholarly_adapter import (
    ScholarlyEvidenceAdapter,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.reasoning.contracts import (
    AnswerConstraint,
    ReasoningMode,
    ReligiousDiscipline,
)
from basira.reasoning.routing import (
    ReligiousReasoningRoute,
)
from basira.retrieval.arabic_query import (
    normalize_arabic_search_text,
)
from basira.retrieval.scholarly_lexical import (
    ScholarlyLexicalHit,
    ScholarlyLexicalIndex,
)
from basira.sources.shamela.contracts import (
    ShamelaCorpusManifest,
    ShamelaPassageIdentity,
)


class ShamelaSearchStrategy(StrEnum):
    """
    Search operations available before semantic
    verification exists.

    No strategy here is an entailment check.
    """

    METADATA_FILTER = "metadata_filter"

    LEXICAL = "lexical"


class ShamelaScoutStopReason(StrEnum):
    """
    Why the bounded evidence scout stopped.

    RETRIEVAL_COVERAGE_MET is deliberately named as
    retrieval coverage, not semantic support.
    """

    RETRIEVAL_COVERAGE_MET = "retrieval_coverage_met"

    RESOLVED_ABSENCE = "resolved_absence"

    BUDGET_EXHAUSTED = "budget_exhausted"

    SOURCE_UNAVAILABLE = "source_unavailable"

    EXPERT_REVIEW_REQUIRED = "expert_review_required"

    NOT_APPLICABLE = "not_applicable"


_MADHHAB_CUES: dict[
    str,
    tuple[str, ...],
] = {
    "hanafi": (
        "حنفي",
        "الحنفي",
        "الحنفية",
    ),
    "maliki": (
        "مالكي",
        "المالكي",
        "المالكية",
    ),
    "shafii": (
        "شافعي",
        "الشافعي",
        "الشافعية",
    ),
    "hanbali": (
        "حنبلي",
        "الحنبلي",
        "الحنبلية",
        "الحنابلة",
    ),
    "zahiri": (
        "ظاهري",
        "الظاهري",
        "الظاهرية",
    ),
    "jafari": (
        "جعفري",
        "الجعفري",
        "الجعفرية",
        "الامامية",
        "الإمامية",
    ),
}


_CONTEMPORARY_CLASSICAL_BRIDGE_RULES = (
    (
        (
            "بيتكوين",
            "bitcoin",
            "crypto",
            "عملة رقمية",
            "عملات رقمية",
            "العملات الرقمية",
        ),
        (
            "المال",
            "البيع",
            "الصرف",
            "التقابض",
        ),
    ),
)


def _classical_bridge_query(
    question: str,
) -> str:
    """
    Project bounded contemporary vocabulary into
    classical retrieval vocabulary.

    Retrieval planning only:
    - no evidence IDs;
    - no authority judgment;
    - no religious ruling;
    - no semantic support verdict.
    """

    normalized = normalize_arabic_search_text(question).casefold()

    for cues, classical_terms in _CONTEMPORARY_CLASSICAL_BRIDGE_RULES:
        if any(
            normalize_arabic_search_text(cue).casefold() in normalized for cue in cues
        ):
            return " ".join(classical_terms)

    return question


def _detect_requested_madhhabs(
    question: str,
) -> tuple[
    str,
    ...,
]:
    normalized = normalize_arabic_search_text(question).casefold()

    return tuple(
        madhhab
        for madhhab, cues in _MADHHAB_CUES.items()
        if any(
            normalize_arabic_search_text(cue).casefold() in normalized for cue in cues
        )
    )


def _domains_for_route(
    route: ReligiousReasoningRoute,
) -> tuple[
    ScholarlyDomain,
    ...,
]:
    disciplines = (
        route.frame.primary_discipline,
        *route.frame.secondary_disciplines,
    )

    domains: list[ScholarlyDomain] = []

    seen: set[ScholarlyDomain] = set()

    def add(
        domain: ScholarlyDomain,
    ) -> None:
        if domain in seen:
            return

        seen.add(domain)
        domains.append(domain)

    for discipline in disciplines:
        if discipline in {
            ReligiousDiscipline.FIQH,
            ReligiousDiscipline.USUL_AL_FIQH,
            ReligiousDiscipline.MAWARITH,
        }:
            add(ScholarlyDomain.FIQH)

        elif discipline is ReligiousDiscipline.CONTEMPORARY_FIQH:
            add(ScholarlyDomain.FATWA)

        elif discipline is ReligiousDiscipline.AQIDAH:
            add(ScholarlyDomain.AQIDAH)

        elif discipline is ReligiousDiscipline.SIRAH:
            add(ScholarlyDomain.SIRA)

        elif discipline is ReligiousDiscipline.TAFSIR:
            add(ScholarlyDomain.TAFSIR)

        elif discipline is ReligiousDiscipline.ASBAB_AL_NUZUL:
            add(ScholarlyDomain.REVELATION_CONTEXT)

    return tuple(domains)


def _book_family_hints(
    domains: tuple[
        ScholarlyDomain,
        ...,
    ],
) -> tuple[
    str,
    ...,
]:
    hints: list[str] = []

    for domain in domains:
        if domain is ScholarlyDomain.FIQH:
            hints.append("classical_fiqh")

        elif domain is ScholarlyDomain.FATWA:
            hints.append("contemporary_fatwa")

        elif domain is ScholarlyDomain.TAFSIR:
            hints.append("tafsir")

        elif domain is ScholarlyDomain.AQIDAH:
            hints.append("aqidah")

        elif domain is ScholarlyDomain.SIRA:
            hints.append("sira")

    return tuple(dict.fromkeys(hints))


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaSearchTask:
    task_id: str

    query: str

    domains: tuple[
        ScholarlyDomain,
        ...,
    ]

    requested_madhhabs: tuple[
        str,
        ...,
    ] = ()

    excluded_madhhabs: tuple[
        str,
        ...,
    ] = ()

    book_family_hints: tuple[
        str,
        ...,
    ] = ()

    # Immutable work-level retrieval scope.

    # Empty + no fingerprint means legacy/unbound search.
    # Empty + fingerprint means policy-bound allow-none
    # and must fail closed in every backend.
    allowed_work_ids: tuple[
        str,
        ...,
    ] = ()

    policy_fingerprint: str | None = None

    strategies: tuple[
        ShamelaSearchStrategy,
        ...,
    ] = (
        ShamelaSearchStrategy.METADATA_FILTER,
        ShamelaSearchStrategy.LEXICAL,
    )

    require_parent_context: bool = True

    reason: str = "initial_search"


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaScoutPlan:
    """
    Bounded search plan produced from Basira's
    religious reasoning route.

    max_passes and max_subqueries are intentionally
    hard-bounded so an agent cannot search forever.
    """

    plan_id: str

    question: str

    required_domains: tuple[
        ScholarlyDomain,
        ...,
    ]

    requested_madhhabs: tuple[
        str,
        ...,
    ]

    comparative: bool

    preserve_disagreement: bool

    book_family_hints: tuple[
        str,
        ...,
    ]

    initial_tasks: tuple[
        ShamelaSearchTask,
        ...,
    ]

    # Immutable policy material propagated to every
    # adaptive/repair query created from this plan.
    allowed_work_ids: tuple[
        str,
        ...,
    ] = ()

    policy_fingerprint: str | None = None

    max_passes: int = 3

    max_subqueries: int = 3

    def __post_init__(
        self,
    ) -> None:
        if not 1 <= self.max_passes <= 3:
            raise ValueError("max_passes must be between 1 and 3")

        if not 1 <= self.max_subqueries <= 3:
            raise ValueError("max_subqueries must be between 1 and 3")


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaSearchHit:
    passage: ScholarlyPassage

    identity: ShamelaPassageIdentity

    score: float

    parent_context: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaScoutObservation:
    pass_number: int

    task_ids: tuple[
        str,
        ...,
    ]

    new_evidence_ids: tuple[
        str,
        ...,
    ]

    covered_domains: tuple[
        ScholarlyDomain,
        ...,
    ]

    covered_madhhabs: tuple[
        str,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaScoutResult:
    plan: ShamelaScoutPlan

    evidence: tuple[
        EvidenceNode,
        ...,
    ]

    hits: tuple[
        ShamelaSearchHit,
        ...,
    ]

    observations: tuple[
        ShamelaScoutObservation,
        ...,
    ]

    stop_reason: ShamelaScoutStopReason

    unresolved_domains: tuple[
        ScholarlyDomain,
        ...,
    ]

    unresolved_madhhabs: tuple[
        str,
        ...,
    ]

    passes_used: int

    subqueries_used: int

    executed_query_hints: tuple[
        str,
        ...,
    ] = ()

    @property
    def has_evidence(
        self,
    ) -> bool:
        return bool(self.evidence)


class ShamelaSearchBackend(Protocol):
    """
    Deterministic retrieval boundary.

    A backend returns source-derived passages only.
    It cannot generate claims or evidence.
    """

    @property
    def is_available(
        self,
    ) -> bool: ...

    @property
    def attests_complete_absence(
        self,
    ) -> bool: ...

    def search(
        self,
        task: ShamelaSearchTask,
        *,
        limit: int = 10,
    ) -> tuple[
        ShamelaSearchHit,
        ...,
    ]: ...


class ShamelaPlanningAdvisor(Protocol):
    """
    Optional model-backed planning component.

    It may propose search queries only.

    It is deliberately unable to return evidence IDs,
    passages, religious rulings, source authority
    judgments, or final answers.
    """

    def propose_queries(
        self,
        *,
        plan: ShamelaScoutPlan,
        observations: tuple[
            ShamelaScoutObservation,
            ...,
        ],
        max_queries: int,
    ) -> tuple[
        str,
        ...,
    ]: ...


class ShamelaScoutPlanner:
    def build(
        self,
        route: ReligiousReasoningRoute,
    ) -> ShamelaScoutPlan:
        domains = _domains_for_route(route)

        requested_madhhabs = _detect_requested_madhhabs(route.frame.question)

        comparative = route.frame.reasoning_mode is ReasoningMode.COMPARATIVE

        preserve_disagreement = (
            AnswerConstraint.PRESERVE_DISAGREEMENT in route.frame.constraints
        )

        family_hints = _book_family_hints(domains)

        initial_tasks: tuple[
            ShamelaSearchTask,
            ...,
        ]

        if domains:
            initial_tasks = (
                ShamelaSearchTask(
                    task_id=("shamela:initial"),
                    query=(route.frame.question),
                    domains=domains,
                    requested_madhhabs=(requested_madhhabs),
                    book_family_hints=(family_hints),
                    reason=("reasoning_route"),
                ),
            )
        else:
            initial_tasks = ()

        return ShamelaScoutPlan(
            plan_id=(f"shamela:{route.frame.frame_id}"),
            question=(route.frame.question),
            required_domains=domains,
            requested_madhhabs=(requested_madhhabs),
            comparative=comparative,
            preserve_disagreement=(preserve_disagreement),
            book_family_hints=(family_hints),
            initial_tasks=(initial_tasks),
        )

    def next_tasks(
        self,
        *,
        plan: ShamelaScoutPlan,
        hits: tuple[
            ShamelaSearchHit,
            ...,
        ],
        observations: tuple[
            ShamelaScoutObservation,
            ...,
        ],
        remaining_subqueries: int,
        advisor: (ShamelaPlanningAdvisor | None) = None,
    ) -> tuple[
        ShamelaSearchTask,
        ...,
    ]:
        if remaining_subqueries <= 0:
            return ()

        covered_domains = {hit.passage.domain for hit in hits}

        covered_madhhabs = {
            hit.identity.madhhab for hit in hits if hit.identity.madhhab
        }

        tasks: list[ShamelaSearchTask] = []

        for domain in plan.required_domains:
            if domain in covered_domains:
                continue

            repair_query = plan.question
            repair_reason = "repair_missing_domain"

            if (
                domain is ScholarlyDomain.FIQH
                and ScholarlyDomain.FATWA in plan.required_domains
            ):
                repair_query = _classical_bridge_query(plan.question)
                repair_reason = "bridge_contemporary_to_classical_fiqh"

            tasks.append(
                ShamelaSearchTask(
                    task_id=(f"shamela:missing-domain:{domain.value}"),
                    query=repair_query,
                    domains=(domain,),
                    requested_madhhabs=(plan.requested_madhhabs),
                    book_family_hints=(plan.book_family_hints),
                    allowed_work_ids=(plan.allowed_work_ids),
                    policy_fingerprint=(plan.policy_fingerprint),
                    reason=repair_reason,
                )
            )

            if len(tasks) >= remaining_subqueries:
                return tuple(tasks)
        missing_madhhabs = tuple(
            madhhab
            for madhhab in plan.requested_madhhabs
            if madhhab not in covered_madhhabs
        )

        for madhhab in missing_madhhabs:
            tasks.append(
                ShamelaSearchTask(
                    task_id=(f"shamela:missing-madhhab:{madhhab}"),
                    query=plan.question,
                    domains=(plan.required_domains),
                    requested_madhhabs=(madhhab,),
                    book_family_hints=(plan.book_family_hints),
                    allowed_work_ids=(plan.allowed_work_ids),
                    policy_fingerprint=(plan.policy_fingerprint),
                    reason=("repair_missing_madhhab"),
                )
            )

            if len(tasks) >= remaining_subqueries:
                return tuple(tasks)

        if (
            plan.comparative
            and not plan.requested_madhhabs
            and len(covered_madhhabs) < 2
        ):
            tasks.append(
                ShamelaSearchTask(
                    task_id=("shamela:diversity-repair"),
                    query=plan.question,
                    domains=(plan.required_domains),
                    excluded_madhhabs=(tuple(sorted(covered_madhhabs))),
                    book_family_hints=(plan.book_family_hints),
                    allowed_work_ids=(plan.allowed_work_ids),
                    policy_fingerprint=(plan.policy_fingerprint),
                    reason=("repair_comparative_diversity"),
                )
            )

            if len(tasks) >= remaining_subqueries:
                return tuple(tasks)

        if advisor is not None:
            advisor_budget = remaining_subqueries - len(tasks)

            if advisor_budget > 0:
                suggestions = advisor.propose_queries(
                    plan=plan,
                    observations=(observations),
                    max_queries=(advisor_budget),
                )

                for index, query in enumerate(
                    suggestions[:advisor_budget],
                    start=1,
                ):
                    normalized = " ".join(query.split())

                    if not normalized:
                        continue

                    tasks.append(
                        ShamelaSearchTask(
                            task_id=(f"shamela:advisor:{index}"),
                            query=normalized,
                            domains=(plan.required_domains),
                            requested_madhhabs=(plan.requested_madhhabs),
                            book_family_hints=(plan.book_family_hints),
                            allowed_work_ids=(plan.allowed_work_ids),
                            policy_fingerprint=(plan.policy_fingerprint),
                            reason=("planning_advisor"),
                        )
                    )

        return tuple(tasks[:remaining_subqueries])


class InMemoryShamelaBackend:
    """
    Bounded reference backend for tests and small
    governed snapshots.

    Full Shamela is intentionally NOT loaded into
    memory. R3B can replace this with SQLite/FTS
    while leaving the agent contract unchanged.
    """

    def __init__(
        self,
        passages: Iterable[ScholarlyPassage],
        *,
        manifest: (ShamelaCorpusManifest),
    ) -> None:
        self.manifest = manifest

        allowed_sources = frozenset(manifest.source_ids)

        accepted: list[ScholarlyPassage] = []

        for passage in passages:
            if passage.source_id not in allowed_sources:
                continue

            identity = ShamelaPassageIdentity.from_passage(passage)

            if identity.snapshot_id != manifest.snapshot_id:
                raise ValueError("Shamela passage snapshot_id does not match manifest")

            if identity.snapshot_sha256 != manifest.snapshot_sha256:
                raise ValueError(
                    "Shamela passage snapshot hash does not match manifest"
                )

            accepted.append(passage)

        by_domain: dict[
            ScholarlyDomain,
            list[ScholarlyPassage],
        ] = {}

        for passage in accepted:
            by_domain.setdefault(
                passage.domain,
                [],
            ).append(passage)

        self._indexes = {
            domain: (ScholarlyLexicalIndex(domain_passages))
            for domain, domain_passages in by_domain.items()
        }

    @property
    def is_available(
        self,
    ) -> bool:
        # The governed snapshot itself is configured
        # and available even when a search has no
        # matching passages.
        return True

    @property
    def attests_complete_absence(
        self,
    ) -> bool:
        return self.manifest.attested_complete

    def search(
        self,
        task: ShamelaSearchTask,
        *,
        limit: int = 10,
    ) -> tuple[
        ShamelaSearchHit,
        ...,
    ]:
        if limit <= 0:
            return ()

        candidate_limit = max(
            limit * 8,
            40,
        )

        requested = frozenset(task.requested_madhhabs)

        excluded = frozenset(task.excluded_madhhabs)

        allowed_work_ids = frozenset(
            task.allowed_work_ids
        )

        if (
            task.policy_fingerprint is not None
            and not allowed_work_ids
        ):
            return ()

        collected: list[ShamelaSearchHit] = []

        seen: set[str] = set()

        for domain in task.domains:
            index = self._indexes.get(domain)

            if index is None:
                continue

            lexical_hits = index.search(
                task.query,
                limit=candidate_limit,
            )

            for lexical_hit in lexical_hits:
                hit = self._convert_hit(lexical_hit)

                work_id = str(
                    hit.passage.work_id
                    or ""
                )

                if (
                    allowed_work_ids
                    and work_id
                    not in allowed_work_ids
                ):
                    continue

                madhhab = hit.identity.madhhab

                if requested and madhhab not in requested:
                    continue

                if excluded and madhhab in excluded:
                    continue

                evidence_id = hit.passage.passage_id

                if evidence_id in seen:
                    continue

                seen.add(evidence_id)

                collected.append(hit)

        collected.sort(
            key=lambda hit: (
                -hit.score,
                hit.identity.book_id,
                hit.identity.page_id,
            )
        )

        return tuple(collected[:limit])

    @staticmethod
    def _convert_hit(
        hit: ScholarlyLexicalHit,
    ) -> ShamelaSearchHit:
        identity = ShamelaPassageIdentity.from_passage(hit.passage)

        return ShamelaSearchHit(
            passage=hit.passage,
            identity=identity,
            score=hit.score,
            parent_context=(identity.parent_text),
        )


class ShamelaHybridEvidenceScout:
    """
    Bounded hybrid agent:

    religious reasoning route
        -> deterministic search plan
        -> governed retrieval
        -> structural coverage assessment
        -> bounded re-planning
        -> source-derived EvidenceNodes

    An optional model-backed advisor may suggest
    search strings, but it can never create evidence.
    """

    def __init__(
        self,
        *,
        backend: ShamelaSearchBackend,
        planner: (ShamelaScoutPlanner | None) = None,
        advisor: (ShamelaPlanningAdvisor | None) = None,
    ) -> None:
        self.backend = backend

        self.planner = planner or ShamelaScoutPlanner()

        self.advisor = advisor

        self.adapter = ScholarlyEvidenceAdapter()

    def scout(
        self,
        route: ReligiousReasoningRoute,
        *,
        limit_per_task: int = 10,
    ) -> ShamelaScoutResult:
        plan = self.planner.build(route)

        if not plan.required_domains:
            return self._result(
                plan=plan,
                hits=(),
                observations=(),
                stop_reason=(ShamelaScoutStopReason.NOT_APPLICABLE),
                passes_used=0,
                subqueries_used=0,
            )

        if not self.backend.is_available:
            return self._result(
                plan=plan,
                hits=(),
                observations=(),
                stop_reason=(ShamelaScoutStopReason.SOURCE_UNAVAILABLE),
                passes_used=0,
                subqueries_used=0,
            )

        pending = list(plan.initial_tasks)

        executed_query_hints: list[str] = []

        observations: list[ShamelaScoutObservation] = []

        hits_by_id: dict[
            str,
            ShamelaSearchHit,
        ] = {}

        subqueries_used = 0

        passes_used = 0

        for pass_number in range(
            1,
            plan.max_passes + 1,
        ):
            if not pending or subqueries_used >= plan.max_subqueries:
                break

            passes_used = pass_number

            current_tasks = pending[: (plan.max_subqueries - subqueries_used)]

            pending = []

            new_ids: list[str] = []

            task_ids: list[str] = []

            for task in current_tasks:
                subqueries_used += 1

                executed_query_hints.append(
                    task.query
                )

                task_ids.append(task.task_id)

                task_hits = self.backend.search(
                    task,
                    limit=(limit_per_task),
                )

                for hit in task_hits:
                    evidence_id = hit.passage.passage_id

                    if evidence_id in hits_by_id:
                        continue

                    hits_by_id[evidence_id] = hit

                    new_ids.append(evidence_id)

            all_hits = tuple(hits_by_id.values())

            observation = self._observation(
                pass_number=(pass_number),
                task_ids=tuple(task_ids),
                new_ids=tuple(new_ids),
                hits=all_hits,
            )

            observations.append(observation)

            if self._coverage_met(
                plan=plan,
                hits=all_hits,
            ):
                expert_required = (
                    AnswerConstraint.REQUIRE_EXPERT_REVIEW in route.frame.constraints
                )

                stop_reason = (
                    ShamelaScoutStopReason.EXPERT_REVIEW_REQUIRED
                    if expert_required
                    else ShamelaScoutStopReason.RETRIEVAL_COVERAGE_MET
                )

                return self._result(
                    plan=plan,
                    hits=all_hits,
                    observations=tuple(observations),
                    stop_reason=(stop_reason),
                    passes_used=(passes_used),
                    subqueries_used=(subqueries_used),
            executed_query_hints=(
                tuple(executed_query_hints)
            ),
                )

            remaining = plan.max_subqueries - subqueries_used

            if remaining <= 0:
                break

            pending = list(
                self.planner.next_tasks(
                    plan=plan,
                    hits=all_hits,
                    observations=tuple(observations),
                    remaining_subqueries=(remaining),
                    advisor=self.advisor,
                )
            )

        all_hits = tuple(hits_by_id.values())

        if not all_hits and self.backend.attests_complete_absence:
            stop_reason = ShamelaScoutStopReason.RESOLVED_ABSENCE
        else:
            stop_reason = ShamelaScoutStopReason.BUDGET_EXHAUSTED

        return self._result(
            plan=plan,
            hits=all_hits,
            observations=tuple(observations),
            stop_reason=stop_reason,
            passes_used=passes_used,
            subqueries_used=(subqueries_used),
            executed_query_hints=(
                tuple(executed_query_hints)
            ),
        )

    def _result(
        self,
        *,
        plan: ShamelaScoutPlan,
        hits: tuple[
            ShamelaSearchHit,
            ...,
        ],
        observations: tuple[
            ShamelaScoutObservation,
            ...,
        ],
        stop_reason: (ShamelaScoutStopReason),
        passes_used: int,
        subqueries_used: int,
        executed_query_hints: tuple[
            str,
            ...,
        ] = (),
    ) -> ShamelaScoutResult:
        evidence = tuple(self.adapter.from_passage(hit.passage) for hit in hits)

        covered_domains = {hit.passage.domain for hit in hits}

        unresolved_domains = tuple(
            domain for domain in plan.required_domains if domain not in covered_domains
        )

        covered_madhhabs = {
            hit.identity.madhhab for hit in hits if hit.identity.madhhab
        }

        unresolved_madhhabs = tuple(
            madhhab
            for madhhab in plan.requested_madhhabs
            if madhhab not in covered_madhhabs
        )

        return ShamelaScoutResult(
            plan=plan,
            evidence=evidence,
            hits=hits,
            observations=(observations),
            stop_reason=(stop_reason),
            unresolved_domains=(unresolved_domains),
            unresolved_madhhabs=(unresolved_madhhabs),
            passes_used=passes_used,
            subqueries_used=(subqueries_used),
            executed_query_hints=(
                tuple(executed_query_hints)
            ),
        )

    @staticmethod
    def _observation(
        *,
        pass_number: int,
        task_ids: tuple[
            str,
            ...,
        ],
        new_ids: tuple[
            str,
            ...,
        ],
        hits: tuple[
            ShamelaSearchHit,
            ...,
        ],
    ) -> ShamelaScoutObservation:
        domains = tuple(
            sorted(
                {hit.passage.domain for hit in hits},
                key=lambda value: value.value,
            )
        )

        madhhabs = tuple(
            sorted({hit.identity.madhhab for hit in hits if hit.identity.madhhab})
        )

        return ShamelaScoutObservation(
            pass_number=pass_number,
            task_ids=task_ids,
            new_evidence_ids=(new_ids),
            covered_domains=domains,
            covered_madhhabs=(madhhabs),
        )

    @staticmethod
    def _coverage_met(
        *,
        plan: ShamelaScoutPlan,
        hits: tuple[
            ShamelaSearchHit,
            ...,
        ],
    ) -> bool:
        covered_domains = {hit.passage.domain for hit in hits}

        if not set(plan.required_domains).issubset(covered_domains):
            return False

        covered_madhhabs = {
            hit.identity.madhhab for hit in hits if hit.identity.madhhab
        }

        if plan.requested_madhhabs:
            if not set(plan.requested_madhhabs).issubset(covered_madhhabs):
                return False

        elif plan.comparative:
            if len(covered_madhhabs) < 2:
                return False

        return bool(hits)
