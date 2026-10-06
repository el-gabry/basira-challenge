from __future__ import annotations

from dataclasses import (
    dataclass,
    replace,
)

from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
)
from basira.orchestration.claim_sufficiency import (
    ClaimDependencyResolver,
    ClaimResolutionResult,
    ClaimSufficiencyAssessment,
    ClaimSufficiencyContract,
    ClaimSufficiencyEvaluator,
)
from basira.orchestration.contracts import (
    AgentCapability,
    AgentExecutionResult,
    AgentExecutionStatus,
    ClaimTask,
    DelegationRequest,
)
from basira.orchestration.coordinator import (
    AgentRunProduct,
)
from basira.orchestration.evidence_acceptance import (
    ClaimEvidencePolicySet,
    TaskEvidenceAcceptanceResult,
    TaskEvidenceAcceptanceService,
)
from basira.orchestration.evidence_relation import (
    TaskEvidenceRelationAssessment,
    TaskEvidenceRelationService,
)
from basira.orchestration.retrieval_constraints import (
    RetrievalConstraintProjectionError,
    project_contract_onto_plan,
)
from basira.reasoning.routing import (
    ReasoningEvidenceAdapter,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlan,
    BasiraRetrievalPlanner,
    RetrievalTarget,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
    UnifiedRetrievalResult,
)


class CapabilityExecutionError(RuntimeError):
    """
    Base failure for the concrete capability execution
    boundary.
    """


class UnregisteredCapabilityExecution(CapabilityExecutionError):
    """
    Execution was requested for a capability that has
    no pre-registered retrieval binding.
    """


class CapabilityRetrievalMismatch(CapabilityExecutionError):
    """
    The registered capability cannot safely execute any
    target already present in the baseline retrieval
    plan.

    The executor fails closed instead of adding a new
    target or widening retrieval scope.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class CapabilityRetrievalBinding:
    """
    Source-agnostic execution binding.

    `domains` is a narrowing allowlist over targets
    already produced by BasiraRetrievalPlanner.

    It is NOT:
    - a source allowlist;
    - a book allowlist;
    - an authority declaration;
    - a runtime permission;
    - a substitute for domain source governance.
    """

    capability_id: str

    domains: frozenset[EvidenceDomain]

    limit_per_domain: int = 10

    def __post_init__(
        self,
    ) -> None:
        if not self.capability_id.strip():
            raise ValueError("capability_id must not be blank")

        if not self.domains:
            raise ValueError("capability binding requires at least one domain")

        if self.limit_per_domain <= 0:
            raise ValueError("limit_per_domain must be positive")


class GovernedCapabilityExecutor:
    """
    Concrete Agent V1 execution adapter.

    Flow:
        ClaimTask
        -> existing query understanding
        -> reasoning requirements strengthen baseline
        -> existing BasiraRetrievalPlanner
        -> capability NARROWS existing targets
        -> existing BasiraUnifiedRetriever
        -> AgentRunProduct

    This component has no API for selecting source IDs,
    books, authority levels, or runtime permissions.

    Repeated executions for the same claim accumulate
    only governed UnifiedRetrievalResult objects. This
    lets RETRIEVE_MORE/delegation passes present the
    evidence layer with the complete governed retrieval
    state rather than an untrusted agent-created delta.
    """

    def __init__(
        self,
        *,
        retriever: BasiraUnifiedRetriever,
        bindings: tuple[
            CapabilityRetrievalBinding,
            ...,
        ],
        understanding_service: (BasiraQueryUnderstandingService | None) = None,
        planner: (BasiraRetrievalPlanner | None) = None,
        reasoning_adapter: (ReasoningEvidenceAdapter | None) = None,
        evidence_policies: (ClaimEvidencePolicySet | None) = None,
        relation_service: (TaskEvidenceRelationService | None) = None,
        sufficiency_contracts: tuple[
            ClaimSufficiencyContract,
            ...,
        ] = (),
        sufficiency_evaluator: (ClaimSufficiencyEvaluator | None) = None,
        dependency_resolver: (ClaimDependencyResolver | None) = None,
    ) -> None:
        by_id: dict[
            str,
            CapabilityRetrievalBinding,
        ] = {}

        for binding in bindings:
            capability_id = binding.capability_id.strip()

            if capability_id in by_id:
                raise ValueError(
                    f"duplicate capability retrieval binding: {capability_id}"
                )

            by_id[capability_id] = binding

        if not by_id:
            raise ValueError("at least one capability retrieval binding is required")

        self._retriever = retriever
        self._bindings = by_id

        self._understanding_service = (
            understanding_service or BasiraQueryUnderstandingService()
        )

        self._planner = planner or BasiraRetrievalPlanner()

        self._reasoning_adapter = reasoning_adapter or ReasoningEvidenceAdapter()

        self._retrieval_by_task: dict[
            str,
            UnifiedRetrievalResult,
        ] = {}

        # Raw governed retrieval remains internal.
        # When claim evidence policies are supplied,
        # only structurally accepted evidence may
        # leave this executor.
        self._evidence_policies = evidence_policies

        self._evidence_acceptance_service = (
            TaskEvidenceAcceptanceService(evidence_policies)
            if evidence_policies is not None
            else None
        )

        self._evidence_acceptance_by_task: dict[
            str,
            TaskEvidenceAcceptanceResult,
        ] = {}

        if relation_service is not None and self._evidence_acceptance_service is None:
            raise ValueError(
                "semantic relation runtime requires structural evidence policies"
            )

        sufficiency_by_task: dict[
            str,
            ClaimSufficiencyContract,
        ] = {}

        for contract in sufficiency_contracts:
            if contract.task_id in sufficiency_by_task:
                raise ValueError(
                    f"duplicate claim sufficiency contract task_id: {contract.task_id}"
                )

            sufficiency_by_task[contract.task_id] = contract

        if sufficiency_by_task and relation_service is None:
            raise ValueError(
                "claim sufficiency runtime requires semantic relation service"
            )

        self._relation_service = relation_service

        self._relation_by_task: dict[
            str,
            TaskEvidenceRelationAssessment,
        ] = {}

        self._sufficiency_contracts = sufficiency_by_task

        self._sufficiency_evaluator = (
            sufficiency_evaluator or ClaimSufficiencyEvaluator()
        )

        self._sufficiency_by_task: dict[
            str,
            ClaimSufficiencyAssessment,
        ] = {}

        self._dependency_resolver = dependency_resolver or ClaimDependencyResolver()

    def latest_retrieval(
        self,
        task_id: str,
    ) -> UnifiedRetrievalResult | None:
        """
        Read-only projection useful for trace/evaluation.
        """

        return self._retrieval_by_task.get(task_id)

    @staticmethod
    def _merge_requirements(
        *,
        baseline: ContextRequirement,
        task_requirement: ContextRequirement,
    ) -> ContextRequirement:
        required = frozenset(baseline.required | task_requirement.required)

        optional = frozenset((baseline.optional | task_requirement.optional) - required)

        return ContextRequirement(
            required=required,
            optional=optional,
        )

    def _build_baseline_plan(
        self,
        task: ClaimTask,
    ) -> BasiraRetrievalPlan:
        understanding = self._understanding_service.understand(task.claim_text)

        strengthened = self._reasoning_adapter.strengthen(
            baseline=(understanding.context_requirement),
            frame=task.frame,
        )

        requirement = self._merge_requirements(
            baseline=strengthened,
            task_requirement=(task.context_requirement),
        )

        understanding = replace(
            understanding,
            context_requirement=requirement,
        )

        plan = self._planner.build(understanding)

        # The planner should preserve the understanding
        # requirement. Set it explicitly as a defensive
        # invariant rather than permitting weakening.
        return replace(
            plan,
            context_requirement=requirement,
        )

    def _apply_retrieval_constraints(
        self,
        *,
        task_id: str,
        plan: BasiraRetrievalPlan,
    ) -> BasiraRetrievalPlan:
        if self._evidence_policies is None:
            return plan

        contract = self._evidence_policies.for_task(task_id)

        try:
            return project_contract_onto_plan(
                plan=plan,
                contract=contract,
            )
        except RetrievalConstraintProjectionError as exc:
            raise CapabilityExecutionError(
                "claim evidence contract cannot be projected into retrieval execution"
            ) from exc

    @staticmethod
    def _narrow_plan(
        *,
        plan: BasiraRetrievalPlan,
        binding: CapabilityRetrievalBinding,
    ) -> BasiraRetrievalPlan:
        targets = tuple(
            target for target in plan.targets if target.domain in binding.domains
        )

        if not targets:
            planned_domains = tuple(target.domain.value for target in plan.targets)

            requested_domains = tuple(
                sorted(domain.value for domain in binding.domains)
            )

            raise CapabilityRetrievalMismatch(
                "capability cannot execute any "
                "existing retrieval target; "
                f"planned={planned_domains}, "
                f"binding={requested_domains}"
            )

        original = set(plan.targets)

        if any(target not in original for target in targets):
            raise AssertionError(
                "capability narrowing introduced a new retrieval target"
            )

        return replace(
            plan,
            targets=targets,
        )

    @staticmethod
    def _merge_targets(
        left: tuple[
            RetrievalTarget,
            ...,
        ],
        right: tuple[
            RetrievalTarget,
            ...,
        ],
    ) -> tuple[
        RetrievalTarget,
        ...,
    ]:
        merged: list[RetrievalTarget] = []

        seen: set[RetrievalTarget] = set()

        for target in (
            *left,
            *right,
        ):
            if target in seen:
                continue

            seen.add(target)

            merged.append(target)

        return tuple(merged)

    @staticmethod
    def _merge_retrieval(
        *,
        previous: (UnifiedRetrievalResult | None),
        current: UnifiedRetrievalResult,
    ) -> UnifiedRetrievalResult:
        if previous is None:
            return current

        if previous.plan.understanding != current.plan.understanding:
            raise CapabilityExecutionError(
                "cannot merge retrieval states with different query understanding"
            )

        if previous.plan.context_requirement != current.plan.context_requirement:
            raise CapabilityExecutionError(
                "cannot merge retrieval states with different evidence requirements"
            )

        evidence = []

        seen_evidence_ids: set[str] = set()

        for node in (
            *previous.evidence,
            *current.evidence,
        ):
            if node.evidence_id in seen_evidence_ids:
                continue

            seen_evidence_ids.add(node.evidence_id)

            evidence.append(node)

        unavailable = set(previous.unavailable_domains)

        current_domains = {target.domain for target in current.plan.targets}

        for domain in current_domains:
            if domain in current.unavailable_domains:
                unavailable.add(domain)
            else:
                # A fresh governed successful retrieval
                # resolves an earlier unavailable marker
                # for the same domain.
                unavailable.discard(domain)

        merged_plan = replace(
            previous.plan,
            targets=(
                GovernedCapabilityExecutor._merge_targets(
                    previous.plan.targets,
                    current.plan.targets,
                )
            ),
        )

        return UnifiedRetrievalResult(
            plan=merged_plan,
            evidence=tuple(evidence),
            unavailable_domains=frozenset(unavailable),
        )

    def acceptance_for_task(
        self,
        task_id: str,
    ) -> TaskEvidenceAcceptanceResult | None:
        """
        Return the latest structural acceptance audit
        for a task.

        This is an audit result only. It does not
        imply semantic support or answerability.
        """

        return self._evidence_acceptance_by_task.get(task_id)

    def relation_for_task(
        self,
        task_id: str,
    ) -> TaskEvidenceRelationAssessment | None:
        return self._relation_by_task.get(task_id)

    def sufficiency_for_task(
        self,
        task_id: str,
    ) -> ClaimSufficiencyAssessment | None:
        return self._sufficiency_by_task.get(task_id)

    def resolve_claim_dependencies(
        self,
    ) -> ClaimResolutionResult:
        if not self._sufficiency_contracts:
            raise CapabilityExecutionError("no claim sufficiency contracts configured")

        missing = tuple(
            task_id
            for task_id in self._sufficiency_contracts
            if (task_id not in self._sufficiency_by_task)
        )

        if missing:
            raise CapabilityExecutionError(
                "missing sufficiency assessment for task(s): " + ", ".join(missing)
            )

        return self._dependency_resolver.resolve(
            contracts=tuple(self._sufficiency_contracts.values()),
            assessments=tuple(
                self._sufficiency_by_task[task_id]
                for task_id in self._sufficiency_contracts
            ),
        )

    def execute(
        self,
        *,
        task: ClaimTask,
        capability: AgentCapability,
        delegation: (DelegationRequest | None),
    ) -> AgentRunProduct:
        binding = self._bindings.get(capability.capability_id)

        if binding is None:
            raise UnregisteredCapabilityExecution(
                "capability has no registered "
                "retrieval execution binding: "
                f"{capability.capability_id}"
            )

        if delegation is not None and delegation.task_id != task.task_id:
            raise CapabilityExecutionError(
                "delegation does not belong to execution task"
            )

        if self._evidence_policies is not None:
            try:
                self._evidence_policies.for_task(task.task_id)
            except KeyError as exc:
                raise CapabilityExecutionError(
                    f"missing structural evidence contract for task: {task.task_id}"
                ) from exc

        baseline_plan = self._build_baseline_plan(task)
        baseline_plan = self._apply_retrieval_constraints(
            task_id=task.task_id,
            plan=baseline_plan,
        )

        narrowed_plan = self._narrow_plan(
            plan=baseline_plan,
            binding=binding,
        )

        current = self._retriever.retrieve(
            narrowed_plan,
            limit_per_domain=(binding.limit_per_domain),
        )

        cumulative = self._merge_retrieval(
            previous=(self._retrieval_by_task.get(task.task_id)),
            current=current,
        )

        self._retrieval_by_task[task.task_id] = cumulative

        returned_retrieval = cumulative

        if self._evidence_acceptance_service is not None:
            acceptance = self._evidence_acceptance_service.evaluate(
                task_id=task.task_id,
                evidence=(cumulative.evidence),
            )

            self._evidence_acceptance_by_task[task.task_id] = acceptance

            returned_retrieval = UnifiedRetrievalResult(
                plan=cumulative.plan,
                evidence=(acceptance.accepted_evidence),
                unavailable_domains=(cumulative.unavailable_domains),
            )

            if self._relation_service is not None:
                relation_assessment = self._relation_service.evaluate(
                    task=task,
                    structural=acceptance,
                )

                self._relation_by_task[task.task_id] = relation_assessment

                sufficiency_contract = self._sufficiency_contracts.get(task.task_id)

                if sufficiency_contract is not None:
                    sufficiency_assessment = self._sufficiency_evaluator.assess(
                        contract=(sufficiency_contract),
                        structural=acceptance,
                        relations=(relation_assessment),
                    )

                    self._sufficiency_by_task[task.task_id] = sufficiency_assessment

        execution_result = AgentExecutionResult(
            task_id=task.task_id,
            agent_id=capability.agent_id,
            status=(AgentExecutionStatus.FINISHED),
            # Deliberately empty.
            # Trusted evidence travels only through
            # UnifiedRetrievalResult.
            evidence=(),
            context=(),
            delegations=(),
        )

        return AgentRunProduct(
            result=execution_result,
            retrieval_result=returned_retrieval,
        )
