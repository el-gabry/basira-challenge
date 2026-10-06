from __future__ import annotations

from basira.answer.composer import (
    GroundedAnswerComposer,
)
from basira.answer.draft_claims import (
    DraftClaimGenerator,
)
from basira.answer.final_output import (
    FinalOutputDraft,
    FinalOutputVerifier,
)
from basira.answer.models import (
    StructuredClaim,
)
from basira.answer.semantic_verification import (
    GeneratedClaimSemanticVerifier,
)
from basira.evidence.models import (
    EvidenceNode,
)
from basira.evidence.publication import (
    EvidencePublicationAuthorizer,
)
from basira.models.source_usage import (
    RuntimeUse,
)
from basira.sources.policy_catalog import (
    SourceUsagePolicyNotFoundError,
    get_source_usage_policy,
)


class DenyAllPublicationAuthorizer:
    """
    Fail-closed publication boundary.

    Used whenever a runtime retriever does not expose
    an explicit governed publication authorizer.
    """

    def may_publish(
        self,
        node: EvidenceNode,
    ) -> bool:
        del node
        return False


class CatalogPublicationAuthorizer:
    """
    Compatibility authorizer for existing governed
    runtime tests / legacy trusted source lanes.

    Official public composition does NOT use this;
    it supplies GovernedPublicationLedger instead.
    """

    def may_publish(
        self,
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


class GovernedGroundedAnswerComposer(GroundedAnswerComposer):
    """
    Public composer whose source-publication decision
    comes from an injected runtime authorizer.

    Semantic verification remains a separate mandatory
    publication gate after this authorization step.
    """

    def __init__(
        self,
        *,
        publication_authorizer: EvidencePublicationAuthorizer,
        semantic_verifier: GeneratedClaimSemanticVerifier,
        draft_claim_generator: DraftClaimGenerator | None = None,
    ) -> None:
        super().__init__(
            semantic_verifier=semantic_verifier,
            draft_claim_generator=(draft_claim_generator),
        )

        self.publication_authorizer = publication_authorizer

        self.final_output_verifier = FinalOutputVerifier(
            publication_authorizer=(publication_authorizer),
            semantic_verifier=(semantic_verifier),
        )

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
        Final public-output firewall.

        Claims may reach the renderer only after:
        - explicit evidence binding
        - publication authorization
        - semantic claim/evidence verification
        """

        result = self.final_output_verifier.verify(
            draft=FinalOutputDraft(
                claims=claims,
            ),
            evidence=evidence,
        )

        issues = tuple(
            dict.fromkeys(
                (
                    *(issue.value for issue in result.issues),
                    *(issue.value for issue in result.semantic_issues),
                )
            )
        )

        return (
            result.action.value,
            issues,
        )

    def _may_publish(
        self,
        node: EvidenceNode,
    ) -> bool:
        return self.publication_authorizer.may_publish(node)
