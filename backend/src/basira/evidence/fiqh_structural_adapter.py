from __future__ import annotations

from basira.evidence.fiqh_units import (
    FiqhStructuralUnit,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)


class FiqhStructuralEvidenceAdapter:
    """
    Convert one source-faithful FiqhStructuralUnit into
    typed EvidenceNodes.

    This adapter does not infer any legal meaning.

    A field becomes an EvidenceNode only when that field
    already exists in the structural unit, which itself
    guarantees literal source support.
    """

    def from_unit(
        self,
        unit: FiqhStructuralUnit,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        position_id = (
            f"{unit.unit_id}:position"
        )

        nodes: list[
            EvidenceNode
        ] = [
            self._node(
                unit=unit,
                evidence_id=position_id,
                claim_type="fiqh_position",
                text=unit.exact_text,
                related_fiqh=(
                    unit.parent_passage_id,
                ),
            )
        ]

        if unit.ruling is not None:
            nodes.append(
                self._node(
                    unit=unit,
                    evidence_id=(
                        f"{unit.unit_id}:ruling"
                    ),
                    claim_type=(
                        "fiqh_ruling"
                    ),
                    text=unit.ruling,
                    related_fiqh=(
                        position_id,
                    ),
                )
            )

        if unit.dalil is not None:
            nodes.append(
                self._node(
                    unit=unit,
                    evidence_id=(
                        f"{unit.unit_id}:dalil"
                    ),
                    claim_type=(
                        "fiqh_dalil"
                    ),
                    text=unit.dalil,
                    related_fiqh=(
                        position_id,
                    ),
                )
            )

        if (
            unit.wajh_al_dalala
            is not None
        ):
            nodes.append(
                self._node(
                    unit=unit,
                    evidence_id=(
                        f"{unit.unit_id}:"
                        "wajh-al-dalala"
                    ),
                    claim_type=(
                        "fiqh_wajh_al_dalala"
                    ),
                    text=(
                        unit.wajh_al_dalala
                    ),
                    related_fiqh=(
                        position_id,
                    ),
                )
            )

        for index, condition in enumerate(
            unit.conditions,
            start=1,
        ):
            nodes.append(
                self._node(
                    unit=unit,
                    evidence_id=(
                        f"{unit.unit_id}:"
                        f"condition:{index}"
                    ),
                    claim_type=(
                        "fiqh_condition"
                    ),
                    text=condition,
                    related_fiqh=(
                        position_id,
                    ),
                )
            )

        for index, exception in enumerate(
            unit.exceptions,
            start=1,
        ):
            nodes.append(
                self._node(
                    unit=unit,
                    evidence_id=(
                        f"{unit.unit_id}:"
                        f"exception:{index}"
                    ),
                    claim_type=(
                        "fiqh_exception"
                    ),
                    text=exception,
                    related_fiqh=(
                        position_id,
                    ),
                )
            )

        if (
            unit.disagreement
            is not None
        ):
            nodes.append(
                self._node(
                    unit=unit,
                    evidence_id=(
                        f"{unit.unit_id}:"
                        "disagreement"
                    ),
                    claim_type=(
                        "fiqh_disagreement"
                    ),
                    text=(
                        unit.disagreement
                    ),
                    related_fiqh=(
                        position_id,
                    ),
                )
            )

        return tuple(
            nodes
        )

    @staticmethod
    def _node(
        *,
        unit: FiqhStructuralUnit,
        evidence_id: str,
        claim_type: str,
        text: str,
        related_fiqh: tuple[
            str,
            ...,
        ],
    ) -> EvidenceNode:
        # Defensive invariant:
        # child legal claims must still be literal
        # substrings of the projected source text.
        if text not in unit.exact_text:
            raise ValueError(
                "Structural Fiqh evidence must remain "
                "a literal substring of its source unit."
            )

        return EvidenceNode(
            evidence_id=evidence_id,
            domain=EvidenceDomain.FIQH,
            text=text,
            source_id=unit.source_id,
            source_version=(
                unit.source_version
            ),
            reference=unit.reference,
            source_url=unit.source_url,
            work_id=unit.work_id,
            work_title=unit.work_title,
            author_name=(
                unit.author_name
            ),
            institution=(
                unit.institution
            ),
            publisher=(
                unit.publisher
            ),
            volume=unit.volume,
            page=unit.page,
            topic=unit.issue,
            claim_type=claim_type,

            # Authority attribution, not a system verdict.
            authority_scope=(
                unit.madhhab
            ),

            # Structural relationship only.
            related_fiqh=(
                related_fiqh
            ),
        )
