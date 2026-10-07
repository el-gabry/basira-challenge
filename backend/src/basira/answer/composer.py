from __future__ import annotations

from basira.answer.draft_claims import (
    DeterministicDraftClaimGenerator,
    DraftClaimGenerator,
)
from basira.answer.integrity import (
    ClaimSourceIntegrityVerifier,
)
from basira.answer.models import (
    AnswerCitation,
    GroundedAnswer,
    StructuredClaim,
)
from basira.answer.semantic_verification import (
    GeneratedClaimSemanticVerifier,
    GeneratedClaimVerificationAction,
)
from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceConflictType,
    EvidenceRequirementAssessment,
    EvidenceRequirementState,
)
from basira.evidence.decision import (
    EvidenceDecisionAction,
)
from basira.evidence.models import (
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)
from basira.models.source_usage import (
    RuntimeUse,
)
from basira.sources.policy_catalog import (
    SourceUsagePolicyNotFoundError,
    get_source_usage_policy,
)

_NO_ATTESTED_ENTRY_MESSAGES = {
    EvidenceNeed.REVELATION_CONTEXT: (
        "لا يوجد مدخل مُثبت لهذه الآية في مصدر "
        "أسباب النزول المعتمد حاليًا. وهذا لا يعني "
        "الجزم بعدم وجود سبب نزول في مصادر أخرى."
    ),
}


_PRIMARY_NEED_PRIORITY = (
    EvidenceNeed.REVELATION_CONTEXT,
    EvidenceNeed.HADITH_TEXT,
    EvidenceNeed.TAFSIR,
    EvidenceNeed.FIQH_EVIDENCE,
    EvidenceNeed.CONTEMPORARY_GUIDANCE,
    EvidenceNeed.CANONICAL_TEXT,
    EvidenceNeed.TRANSLATION,
)


class GroundedAnswerComposer:
    """
    Deterministic post-decision answer composer.

    It never treats every retrieved node as equally
    relevant to the user's requested evidence role.

    The primary required evidence role is selected
    first, then only evidence attached to that
    requirement may enter the user-facing answer.
    """

    def __init__(
        self,
        *,
        max_evidence_nodes: int = 3,
        max_excerpt_chars: int = 360,
        semantic_verifier: (GeneratedClaimSemanticVerifier | None) = None,
        draft_claim_generator: DraftClaimGenerator | None = None,
    ) -> None:
        if max_evidence_nodes <= 0:
            raise ValueError("max_evidence_nodes must be positive.")

        if max_excerpt_chars <= 0:
            raise ValueError("max_excerpt_chars must be positive.")

        self.max_evidence_nodes = max_evidence_nodes

        self.max_excerpt_chars = max_excerpt_chars

        self.claim_integrity_verifier = ClaimSourceIntegrityVerifier()

        self.semantic_verifier = semantic_verifier

        if draft_claim_generator is None:
            draft_claim_generator = DeterministicDraftClaimGenerator(
                builder=self._structured_claims,
            )

        self.draft_claim_generator = draft_claim_generator

    def compose(
        self,
        *,
        question: str,
        outcome: EvidenceDecisionOutcome,
    ) -> GroundedAnswer:
        cleaned_question = " ".join(question.split())

        if not cleaned_question:
            raise ValueError("Question cannot be empty.")

        action = outcome.decision.action

        limitations = list(self._bundle_limitations(outcome.bundle))

        has_fiqh_disagreement = any(
            conflict.conflict_type is EvidenceConflictType.FIQH_POSITION
            for conflict in outcome.bundle.conflicts
        )

        if (
            has_fiqh_disagreement
            and action is EvidenceDecisionAction.ANSWER_WITH_LIMITATION
        ):
            limitations.append(
                "توجد أقوال فقهية موثقة مختلفة؛ "
                "عُرض كل قول منسوبًا إلى نطاقه الفقهي "
                "من دون ترجيح آلي أو تصويت بالأغلبية."
            )

        if action is EvidenceDecisionAction.ESCALATE_TO_EXPERT:
            limitations.append(
                "تتطلب هذه الحالة مراجعة خبير مؤهل، لذلك لم تُنشأ إجابة موضوعية مستقلة."
            )

            return self._without_answer(
                question=cleaned_question,
                action=action,
                outcome=outcome,
                limitations=limitations,
            )

        if action is EvidenceDecisionAction.CLARIFY:
            limitations.append(
                "نحتاج إلى تحديد الآية المقصودة قبل متابعة التفسير؛ "
                "هذه حالة عدم حسم للهوية وليست نقصًا في الأدلة."
            )

            return self._without_answer(
                question=cleaned_question,
                action=action,
                outcome=outcome,
                limitations=limitations,
            )

        if action is EvidenceDecisionAction.RETRIEVE_MORE:
            limitations.append(
                "الأدلة الحالية غير كافية؛ يلزم استرجاع أدلة إضافية قبل إنشاء إجابة."
            )

            return self._without_answer(
                question=cleaned_question,
                action=action,
                outcome=outcome,
                limitations=limitations,
            )

        if action is EvidenceDecisionAction.ABSTAIN:
            limitations.append("لا تسمح حالة الأدلة الحالية بتقديم إجابة موثوقة.")

            return self._without_answer(
                question=cleaned_question,
                action=action,
                outcome=outcome,
                limitations=limitations,
            )

        if action not in {
            EvidenceDecisionAction.ANSWER,
            EvidenceDecisionAction.ANSWER_WITH_LIMITATION,
        }:
            raise ValueError(f"Unsupported evidence decision action: {action.value}")

        (
            primary_assessment,
            candidate_nodes,
        ) = self._primary_evidence(outcome.bundle)

        if (
            primary_assessment is not None
            and primary_assessment.state is EvidenceRequirementState.NO_ATTESTED_ENTRY
        ):
            answer = " ".join(limitations).strip()

            return GroundedAnswer(
                question=cleaned_question,
                action=action,
                answer=answer or None,
                citations=(),
                limitations=tuple(limitations),
                evidence_coverage=(outcome.bundle.evidence_coverage),
                resolution_coverage=(outcome.bundle.resolution_coverage),
                used_evidence_ids=(),
                expert_review=(outcome.expert_review),
            )

        publishable_candidates = tuple(
            node for node in candidate_nodes if self._may_publish(node)
        )

        if (
            primary_assessment is not None
            and primary_assessment.need is EvidenceNeed.FIQH_EVIDENCE
        ):
            nodes = self._fiqh_publication_nodes(
                bundle=outcome.bundle,
                primary_assessment=(primary_assessment),
            )
        else:
            nodes = publishable_candidates[: self.max_evidence_nodes]

        if not nodes:
            limitations.append(
                "لا توجد أدلة للمطلب الأساسي "
                "مصرح لها حاليًا بدعم إجابة "
                "موجهة للمستخدم والاستشهاد بها."
            )

            return self._without_answer(
                question=cleaned_question,
                action=action,
                outcome=outcome,
                limitations=limitations,
            )

        citations = tuple(
            self._citation(
                node=node,
                index=index,
            )
            for index, node in enumerate(
                nodes,
                start=1,
            )
        )

        primary_need = (
            primary_assessment.need if primary_assessment is not None else None
        )

        draft = self.draft_claim_generator.generate(
            question=cleaned_question,
            primary_need=primary_need,
            evidence=nodes,
        )

        claims = draft.claims

        (
            semantic_status,
            semantic_issues,
        ) = self._verify_claims_for_publication(
            claims=claims,
            evidence=nodes,
        )

        if semantic_status in {
            GeneratedClaimVerificationAction.REGENERATE.value,
            GeneratedClaimVerificationAction.BLOCK.value,
        }:
            if semantic_status == GeneratedClaimVerificationAction.REGENERATE.value:
                limitations.append(
                    "تعذر اعتماد صياغة الإجابة "
                    "دلاليًا على الأدلة المستشهد "
                    "بها؛ يلزم إعادة التوليد قبل "
                    "النشر."
                )
            else:
                limitations.append(
                    "فشل تحقق دلالي حاسم بين الادعاء والدليل؛ تم حجب الإجابة عن النشر."
                )

            return GroundedAnswer(
                question=cleaned_question,
                action=action,
                answer=None,
                citations=(),
                limitations=tuple(limitations),
                evidence_coverage=(outcome.bundle.evidence_coverage),
                resolution_coverage=(outcome.bundle.resolution_coverage),
                used_evidence_ids=(),
                claims=(),
                semantic_claim_verification=(semantic_status),
                semantic_verification_issues=(semantic_issues),
                expert_review=(outcome.expert_review),
            )

        answer = self._render_verified_claims(
            primary_need=primary_need,
            claims=claims,
            evidence=nodes,
            limitations=(
                tuple(limitations)
                if (action is EvidenceDecisionAction.ANSWER_WITH_LIMITATION)
                else ()
            ),
        )

        return GroundedAnswer(
            question=cleaned_question,
            action=action,
            answer=answer,
            citations=citations,
            limitations=tuple(limitations),
            evidence_coverage=(outcome.bundle.evidence_coverage),
            resolution_coverage=(outcome.bundle.resolution_coverage),
            used_evidence_ids=tuple(node.evidence_id for node in nodes),
            claims=claims,
            semantic_claim_verification=(semantic_status),
            semantic_verification_issues=(semantic_issues),
            expert_review=(outcome.expert_review),
        )

    @staticmethod
    def _primary_evidence(
        bundle: EvidenceBundle,
    ) -> tuple[
        EvidenceRequirementAssessment | None,
        tuple[EvidenceNode, ...],
    ]:
        by_id = {node.evidence_id: node for node in bundle.evidence}

        for need in _PRIMARY_NEED_PRIORITY:
            assessment = bundle.assessment_for(need)

            if assessment is None:
                continue

            if assessment.state is EvidenceRequirementState.NO_ATTESTED_ENTRY:
                return (
                    assessment,
                    (),
                )

            if assessment.state is not EvidenceRequirementState.SATISFIED:
                continue

            nodes = tuple(
                by_id[evidence_id]
                for evidence_id in assessment.evidence_ids
                if evidence_id in by_id
            )

            # Authenticity is a composite evidence role:
            #
            #   matn + attributed grading
            #
            # Keep one matching matn first, then grading
            # observations, then remaining matn variants.
            # This prevents the normal 3-node publication
            # limit from silently dropping every grade.
            if need is EvidenceNeed.HADITH_TEXT:
                grade_assessment = bundle.assessment_for(EvidenceNeed.HADITH_GRADE)

                if (
                    grade_assessment is not None
                    and grade_assessment.state is EvidenceRequirementState.SATISFIED
                ):
                    grade_nodes = tuple(
                        by_id[evidence_id]
                        for evidence_id in grade_assessment.evidence_ids
                        if evidence_id in by_id
                    )

                    if nodes and grade_nodes:
                        nodes = nodes[:1] + grade_nodes + nodes[1:]

            # Quran interpretation is a composite evidence role:
            #
            #   canonical Quran text + Tafsir explanation
            #
            # Sufficiency already established both requirements.
            # This controls only the bounded publication set.
            if need is EvidenceNeed.TAFSIR:
                canonical_assessment = bundle.assessment_for(
                    EvidenceNeed.CANONICAL_TEXT
                )

                canonical_nodes = ()

                if (
                    canonical_assessment is not None
                    and canonical_assessment.state is EvidenceRequirementState.SATISFIED
                ):
                    canonical_nodes = tuple(
                        by_id[evidence_id]
                        for evidence_id in canonical_assessment.evidence_ids
                        if (
                            evidence_id in by_id
                            and by_id[evidence_id].claim_type == "quran_text"
                        )
                    )

                # Only Quran interpretation is composite:
                #
                #   canonical Quran + focused Tafsir
                #
                # Plain Tafsir-only questions keep the normal
                # multi-node composer behavior unchanged.
                if canonical_nodes:
                    focused_tafsir = tuple(
                        node
                        for node in nodes
                        if (node.claim_type == "tafsir_linguistic_explanation")
                    )

                    supporting_tafsir = tuple(
                        node
                        for node in nodes
                        if (node.claim_type != "tafsir_linguistic_explanation")
                    )

                    if focused_tafsir:
                        selected_tafsir = focused_tafsir[:1]
                    else:
                        selected_tafsir = supporting_tafsir[:1]

                    nodes = canonical_nodes[:1] + selected_tafsir

            return (
                assessment,
                nodes,
            )

        return (
            None,
            bundle.evidence,
        )

    def _fiqh_publication_nodes(
        self,
        *,
        bundle: EvidenceBundle,
        primary_assessment: EvidenceRequirementAssessment,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        """
        Build the complete publication set for Fiqh.

        Fiqh publication is issue-complete, not
        max-node-complete.

        A selected madhhab position carries its complete
        source-backed structural children:

        - ruling
        - dalil
        - wajh al-dalala
        - conditions
        - exceptions
        - disagreement

        No missing field is inferred or manufactured.
        """

        by_id = {node.evidence_id: node for node in bundle.evidence}

        root_ids: list[str] = []
        seen_root_ids: set[str] = set()

        for evidence_id in primary_assessment.evidence_ids:
            node = by_id.get(evidence_id)

            if node is None:
                continue

            if node.claim_type == "fiqh_position":
                root_id = node.evidence_id
            elif node.claim_type == "fiqh_ruling" and node.related_fiqh:
                root_id = node.related_fiqh[0]
            else:
                continue

            if root_id in seen_root_ids:
                continue

            root_node = by_id.get(root_id)

            if root_node is None or root_node.claim_type != "fiqh_position":
                continue

            seen_root_ids.add(root_id)

            root_ids.append(root_id)

        # Defensive fallback:
        # a structurally valid Fiqh bundle should expose
        # position roots through FIQH_EVIDENCE. If a legacy
        # bundle does not, preserve every explicit position
        # rather than silently falling back to three nodes.
        if not root_ids:
            for node in bundle.evidence:
                if node.claim_type != "fiqh_position":
                    continue

                if node.evidence_id in seen_root_ids:
                    continue

                seen_root_ids.add(node.evidence_id)

                root_ids.append(node.evidence_id)

        child_priority = {
            "fiqh_ruling": 10,
            "fiqh_dalil": 20,
            "fiqh_wajh_al_dalala": 30,
            "fiqh_condition": 40,
            "fiqh_exception": 50,
            "fiqh_disagreement": 60,
        }

        selected: list[EvidenceNode] = []

        selected_ids: set[str] = set()

        for root_id in root_ids:
            root = by_id[root_id]

            if self._may_publish(root) and root.evidence_id not in selected_ids:
                selected.append(root)

                selected_ids.add(root.evidence_id)

            children = [
                node
                for node in bundle.evidence
                if (root_id in node.related_fiqh and node.claim_type in child_priority)
            ]

            children.sort(
                key=lambda node: (
                    child_priority[node.claim_type],
                    node.evidence_id,
                )
            )

            for child in children:
                if child.evidence_id in selected_ids:
                    continue

                if not self._may_publish(child):
                    continue

                selected.append(child)

                selected_ids.add(child.evidence_id)

        return tuple(selected)

    @staticmethod
    def _may_publish(
        node: EvidenceNode,
    ) -> bool:
        try:
            policy = get_source_usage_policy(node.source_id)
        except SourceUsagePolicyNotFoundError:
            return False

        if policy.requires_human_review:
            return False

        return policy.allows(RuntimeUse.SUPPORT_ANSWER) and policy.allows(
            RuntimeUse.CITE_TO_USER
        )

    @staticmethod
    def _citation(
        *,
        node: EvidenceNode,
        index: int,
    ) -> AnswerCitation:
        return AnswerCitation(
            marker=f"[{index}]",
            evidence_id=node.evidence_id,
            domain=node.domain,
            source_id=node.source_id,
            source_version=(node.source_version),
            reference=node.reference,
            source_url=node.source_url,
            work_title=node.work_title,
            author_name=node.author_name,
            institution=node.institution,
            publisher=node.publisher,
        )

    def _structured_claims(
        self,
        *,
        primary_need: EvidenceNeed | None,
        nodes: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> tuple[
        StructuredClaim,
        ...,
    ]:
        """
        Build traceable answer units from exactly the
        excerpts that the deterministic composer may
        publish.

        No generated paraphrase is introduced here.
        No semantic support judgment is performed.
        """

        claims: list[StructuredClaim] = []

        for index, node in enumerate(
            nodes,
            start=1,
        ):
            if node.claim_type == "quran_text":
                # Canonical Quran text is literal evidence.
                # Never truncate, paraphrase, or append an
                # ellipsis at the composition boundary.
                text = node.text.strip()
            elif primary_need is EvidenceNeed.REVELATION_CONTEXT:
                text = self._concise_revelation_excerpt(node.text)
            else:
                text = self._excerpt(node.text)

            if not text:
                continue

            if node.claim_type == "quran_text":
                axis_id = node.domain.value
            else:
                axis_id = (
                    primary_need.value
                    if primary_need is not None
                    else node.domain.value
                )

            claims.append(
                StructuredClaim(
                    axis_id=axis_id,
                    claim_id=(f"claim-{index}"),
                    text=text,
                    evidence_ids=(node.evidence_id,),
                )
            )

        return tuple(claims)

    def _verify_claims_for_publication(
        self,
        *,
        claims: tuple[
            StructuredClaim,
            ...,
        ],
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> tuple[
        str,
        tuple[
            str,
            ...,
        ],
    ]:
        """
        Default deterministic verification path.

        Governed public composition overrides this hook
        with the FinalOutputVerifier firewall.

        Legacy/default composer behavior remains
        backward compatible.
        """

        self.claim_integrity_verifier.require_valid(
            claims=claims,
            evidence=evidence,
        )

        if self.semantic_verifier is None:
            return (
                "not_enabled",
                (),
            )

        result = self.semantic_verifier.verify(
            claims=claims,
            evidence=evidence,
        )

        return (
            result.action.value,
            tuple(issue.value for issue in result.issue_types),
        )

    def _render_verified_claims(
        self,
        *,
        primary_need: EvidenceNeed | None,
        claims: tuple[
            StructuredClaim,
            ...,
        ],
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
        limitations: tuple[
            str,
            ...,
        ],
    ) -> str:
        """
        Render only claim units that already passed
        the publication verification path.

        This is the final user-facing boundary.

        Raw evidence nodes must never be rendered again
        after claim verification.
        """

        sections: list[str] = []

        by_id = {node.evidence_id: node for node in evidence}

        if primary_need is EvidenceNeed.FIQH_EVIDENCE:
            return self._render_verified_fiqh_claims(
                claims=claims,
                evidence=evidence,
                limitations=limitations,
            )

        if limitations:
            sections.append("تنبيه: " + " ".join(limitations))

        if primary_need is EvidenceNeed.REVELATION_CONTEXT:
            sections.append("ورد في مصدر أسباب النزول المعتمد:")
        else:
            sections.append("وفق الأدلة المعتمدة:")

        for index, claim in enumerate(
            claims,
            start=1,
        ):
            text = claim.text.strip()

            if not text:
                continue

            grade_node = next(
                (
                    by_id[evidence_id]
                    for evidence_id in claim.evidence_ids
                    if (
                        evidence_id in by_id
                        and by_id[evidence_id].claim_type == "hadith_grade"
                    )
                ),
                None,
            )

            if grade_node is not None:
                grader = (grade_node.author_name or "").strip() or "المحدّث"

                reference = (grade_node.reference or "").strip()

                label = f"حكم {grader}"

                if reference:
                    label += f" ({reference})"

                # `text` is still the exact claim that
                # already passed literal + semantic
                # verification. Only provenance metadata
                # from its own linked evidence is added.
                sections.append(f"[{index}] {label}: {text}")
            else:
                sections.append(f"[{index}] {text}")

        return "\n\n".join(sections)

    def _render_verified_fiqh_claims(
        self,
        *,
        claims: tuple[
            StructuredClaim,
            ...,
        ],
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
        limitations: tuple[
            str,
            ...,
        ],
    ) -> str:
        """
        Render verified Fiqh claims by madhhab position.

        The renderer only reorganizes claims that already
        passed publication verification. It does not infer
        a ruling, evidence, condition, exception, or
        preferred opinion.
        """

        sections: list[str] = []

        if limitations:
            sections.append("تنبيه: " + " ".join(limitations))

        by_id = {node.evidence_id: node for node in evidence}

        claims_by_evidence: dict[
            str,
            list[str],
        ] = {}

        for claim in claims:
            claim_text = claim.text.strip()

            if not claim_text:
                continue

            for evidence_id in claim.evidence_ids:
                if evidence_id not in by_id:
                    continue

                claims_by_evidence.setdefault(
                    evidence_id,
                    [],
                ).append(claim_text)

        positions = tuple(
            node for node in evidence if (node.claim_type == "fiqh_position")
        )

        # Presentation follows the admitted source lane,
        # never a generated translation.
        source_native_english = bool(positions) and all(
            (position.source_id or "").startswith("dorar:fiqh:en:")
            for position in positions
        )

        if source_native_english:
            role_labels = {
                "fiqh_ruling": "Ruling",
                "fiqh_dalil": "Evidence",
                "fiqh_wajh_al_dalala": ("Reasoning from the evidence"),
                "fiqh_condition": "Condition",
                "fiqh_exception": "Exception",
                "fiqh_disagreement": ("Scholarly disagreement"),
            }
        else:
            role_labels = {
                "fiqh_ruling": "الحكم",
                "fiqh_dalil": "الدليل",
                "fiqh_wajh_al_dalala": ("وجه الدلالة"),
                "fiqh_condition": "الشرط",
                "fiqh_exception": ("الاستثناء"),
                "fiqh_disagreement": ("بيان الخلاف"),
            }

        child_priority = {
            "fiqh_ruling": 10,
            "fiqh_dalil": 20,
            "fiqh_wajh_al_dalala": 30,
            "fiqh_condition": 40,
            "fiqh_exception": 50,
            "fiqh_disagreement": 60,
        }

        for position in positions:
            scope = (position.authority_scope or "").strip()

            normalized_scope = scope.lower().replace("_", "-").replace("’", "'")

            if source_native_english:
                madhhab_labels = {
                    "hanafi": "Hanafi school",
                    "maliki": "Maliki school",
                    "shafii": "Shafi'i school",
                    "shafi-i": "Shafi'i school",
                    "shafi'i": "Shafi'i school",
                    "hanbali": "Hanbali school",
                }
            else:
                madhhab_labels = {
                    "hanafi": ("المذهب الحنفي"),
                    "maliki": ("المذهب المالكي"),
                    "shafii": ("المذهب الشافعي"),
                    "shafi-i": ("المذهب الشافعي"),
                    "shafi'i": ("المذهب الشافعي"),
                    "hanbali": ("المذهب الحنبلي"),
                }

            heading = madhhab_labels.get(normalized_scope) or (
                (f"Fiqh scope: {scope}" if scope else "Verified fiqh position")
                if source_native_english
                else (f"النطاق الفقهي: {scope}" if scope else "قول فقهي موثق")
            )

            group_lines: list[str] = [heading]

            position_claims = claims_by_evidence.get(
                position.evidence_id,
                [],
            )

            for claim_text in position_claims:
                group_lines.append(
                    ("Fiqh position: " if source_native_english else "الموقف الفقهي: ")
                    + claim_text
                )

            children = [
                node
                for node in evidence
                if (
                    position.evidence_id in node.related_fiqh
                    and node.claim_type in role_labels
                )
            ]

            children.sort(
                key=lambda node: (
                    child_priority[node.claim_type],
                    node.evidence_id,
                )
            )

            for child in children:
                label = role_labels[child.claim_type]

                child_claims = claims_by_evidence.get(
                    child.evidence_id,
                    [],
                )

                for claim_text in child_claims:
                    group_lines.append(f"{label}: {claim_text}")

            sections.append("\n".join(group_lines))

        # Defensive fallback. If verified Fiqh evidence
        # somehow contains no position root, preserve the
        # verified claims instead of silently discarding
        # them.
        if not positions:
            sections.append(
                "Verified fiqh positions:"
                if source_native_english
                else "الأقوال الفقهية الموثقة:"
            )

            for index, claim in enumerate(
                claims,
                start=1,
            ):
                claim_text = claim.text.strip()

                if claim_text:
                    sections.append(f"[{index}] {claim_text}")

        return "\n\n".join(sections)

    def _render_answer(
        self,
        *,
        primary_need: EvidenceNeed | None,
        nodes: tuple[
            EvidenceNode,
            ...,
        ],
        limitations: tuple[
            str,
            ...,
        ],
    ) -> str:
        sections: list[str] = []

        if limitations:
            sections.append("تنبيه: " + " ".join(limitations))

        if primary_need is EvidenceNeed.REVELATION_CONTEXT:
            sections.append("ورد في مصدر أسباب النزول المعتمد:")
        elif any(node.claim_type == "hadith_grade" for node in nodes):
            sections.append(
                "وفق نص الحديث وأحكام المحدّثين الموجودة في المصادر المعتمدة:"
            )
        else:
            sections.append("وفق الأدلة المعتمدة:")

        for index, node in enumerate(
            nodes,
            start=1,
        ):
            excerpt = (
                self._concise_revelation_excerpt(node.text)
                if (primary_need is EvidenceNeed.REVELATION_CONTEXT)
                else self._excerpt(node.text)
            )

            if not excerpt:
                continue

            if node.claim_type == "hadith_grade":
                grader = (node.author_name or "").strip() or "المحدّث"

                reference = (node.reference or "").strip()

                label = f"حكم {grader}"

                if reference:
                    label += f" ({reference})"

                # Exact source-derived grade wording.
                # If the source itself says
                # "المجمع على صحته", it is preserved
                # here WITH attribution.
                #
                # We never synthesize:
                # "أجمع العلماء"
                # from the number of agreeing records.
                sections.append(f"[{index}] {label}: {excerpt}")
            else:
                sections.append(f"[{index}] {excerpt}")

        return "\n\n".join(sections)

    def _excerpt(
        self,
        text: str,
    ) -> str:
        cleaned = " ".join(text.split())

        if len(cleaned) <= self.max_excerpt_chars:
            return cleaned

        candidate = cleaned[: self.max_excerpt_chars]

        minimum = self.max_excerpt_chars // 2

        best_end = -1

        for separator in (
            "؟",
            "!",
            ".",
            "؛",
        ):
            position = candidate.rfind(separator)

            if position >= minimum:
                best_end = max(
                    best_end,
                    position + 1,
                )

        if best_end > 0:
            return candidate[:best_end].strip()

        return candidate.rstrip() + "…"

    def _concise_revelation_excerpt(
        self,
        text: str,
    ) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        if not lines:
            return ""

        # The source may begin by reproducing the Quran
        # passage. Keep it in evidence, but do not repeat
        # it as the answer to a revelation-context query.
        if lines[0].startswith("قال تعالى:"):
            lines = lines[1:]

        if not lines:
            return ""

        # Prefer the first numbered attested narration,
        # e.g. "288 - ...". Do not run it through the
        # generic character-based excerpt function:
        # publication must not stop mid-sentence.
        for line in lines:
            number, separator, remainder = line.partition(" - ")

            if separator and number.strip().isdigit() and remainder.strip():
                return remainder.strip()

        # Fallback for sources without catalogue numbering.
        # Return the first complete source line rather than
        # cutting by character count.
        return lines[0]

    @staticmethod
    def _bundle_limitations(
        bundle: EvidenceBundle,
    ) -> tuple[str, ...]:
        limitations: list[str] = []

        for assessment in bundle.required_assessments:
            if assessment.state is EvidenceRequirementState.SATISFIED:
                continue

            if assessment.state is EvidenceRequirementState.NO_ATTESTED_ENTRY:
                limitations.append(
                    _NO_ATTESTED_ENTRY_MESSAGES.get(
                        assessment.need,
                        (
                            "لا يوجد مدخل مُثبت في "
                            "المصدر المعتمد حاليًا "
                            "للمتطلب: "
                            f"{assessment.need.value}."
                        ),
                    )
                )
                continue

            if assessment.state is EvidenceRequirementState.UNAVAILABLE_DOMAIN:
                limitations.append(
                    f"مجال الأدلة المطلوب غير متاح حاليًا: {assessment.need.value}."
                )
                continue

            if assessment.state is EvidenceRequirementState.MISSING_EVIDENCE:
                limitations.append(
                    f"الأدلة المطلوبة غير مكتملة للمتطلب: {assessment.need.value}."
                )

        return tuple(limitations)

    @staticmethod
    def _without_answer(
        *,
        question: str,
        action: EvidenceDecisionAction,
        outcome: EvidenceDecisionOutcome,
        limitations: list[str],
    ) -> GroundedAnswer:
        return GroundedAnswer(
            question=question,
            action=action,
            answer=None,
            citations=(),
            limitations=tuple(limitations),
            evidence_coverage=(outcome.bundle.evidence_coverage),
            resolution_coverage=(outcome.bundle.resolution_coverage),
            used_evidence_ids=(),
            expert_review=(outcome.expert_review),
        )
