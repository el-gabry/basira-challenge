from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.retrieval.hadith_index import (
    HadithEvidenceBundle,
    HadithRetrievalHit,
)


class HadithEvidenceAdapter:
    """
    Convert trusted Hadith retrieval results into the
    unified Basira EvidenceNode contract.

    Text, translations, and grade assessments remain
    separate evidence observations with provenance.
    """

    def from_hit(
        self,
        hit: HadithRetrievalHit,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        return self.from_bundle(
            hit.bundle
        )

    def from_bundle(
        self,
        bundle: HadithEvidenceBundle,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        nodes: list[
            EvidenceNode
        ] = []

        conflict_group = (
            bundle.identity.key
            if len(bundle.records) > 1
            else None
        )

        for record in bundle.records:
            reference = (
                record.primary_reference
            )

            reference_value = (
                reference.source_reference
                or (
                    f"{reference.collection_id}:"
                    f"{reference.hadith_number}"
                )
            )

            for index, variant in enumerate(
                record.text_variants
            ):
                nodes.append(
                    EvidenceNode(
                        evidence_id=(
                            f"{record.record_id}:"
                            f"text:{index}"
                        ),
                        domain=(
                            EvidenceDomain.HADITH
                        ),
                        text=(
                            variant.arabic_text
                        ),
                        source_id=(
                            variant.source_id
                        ),
                        reference=(
                            reference_value
                        ),
                        claim_type="hadith_text",
                        related_hadith=(
                            bundle.identity.key,
                        ),
                        conflict_group=(
                            conflict_group
                        ),
                    )
                )

                if (
                    variant.english_translation
                    is not None
                ):
                    nodes.append(
                        EvidenceNode(
                            evidence_id=(
                                f"{record.record_id}:"
                                f"translation:"
                                f"{index}:en"
                            ),
                            domain=(
                                EvidenceDomain
                                .HADITH
                            ),
                            text=(
                                variant
                                .english_translation
                            ),
                            source_id=(
                                variant
                                .translation_source_id
                                or variant.source_id
                            ),
                            reference=(
                                reference_value
                            ),
                            claim_type=(
                                "hadith_translation"
                            ),
                            related_hadith=(
                                bundle.identity.key,
                            ),
                            conflict_group=(
                                conflict_group
                            ),
                        )
                    )

            for index, assessment in enumerate(
                record.grade_assessments
            ):
                grade_reference = (
                    assessment.source_reference
                    or reference_value
                )

                nodes.append(
                    EvidenceNode(
                        evidence_id=(
                            f"{record.record_id}:"
                            f"grade:{index}"
                        ),
                        domain=(
                            EvidenceDomain.HADITH
                        ),
                        text=(
                            assessment.grade_text
                        ),
                        source_id=(
                            assessment.source_id
                        ),
                        source_url=(
                            str(
                                assessment.source_url
                            )
                            if assessment.source_url
                            is not None
                            else None
                        ),
                        reference=(
                            grade_reference
                        ),
                        author_name=(
                            assessment.grader_name
                        ),
                        topic=(
                            assessment.category.value
                        ),
                        claim_type="hadith_grade",
                        related_hadith=(
                            bundle.identity.key,
                        ),
                        conflict_group=(
                            assessment.conflict_group
                            or conflict_group
                        ),
                        conflict_type=(
                            assessment.conflict_type
                        ),
                    )
                )

        return tuple(nodes)
