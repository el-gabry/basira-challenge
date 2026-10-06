from __future__ import annotations

import hashlib
from dataclasses import dataclass

from basira.models.scholarly import ScholarlyPassage


def _clean_optional(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _require_exact_substring(
    *,
    parent: str,
    child: str | None,
    field_name: str,
) -> str | None:
    cleaned = _clean_optional(
        child
    )

    if cleaned is None:
        return None

    if cleaned not in parent:
        raise ValueError(
            f"{field_name} must be an exact "
            "substring of the governed source text."
        )

    return cleaned


def _split_exact_values(
    *,
    parent: str,
    value: str | None,
    field_name: str,
) -> tuple[str, ...]:
    cleaned = _clean_optional(
        value
    )

    if cleaned is None:
        return ()

    values = tuple(
        part.strip()
        for part in cleaned.split("||")
        if part.strip()
    )

    for item in values:
        if item not in parent:
            raise ValueError(
                f"{field_name} item must be an exact "
                "substring of the governed source text."
            )

    return values


def _stable_unit_id(
    *,
    parent_passage_id: str,
    exact_text: str,
) -> str:
    digest = hashlib.sha256()

    digest.update(
        parent_passage_id.encode(
            "utf-8"
        )
    )
    digest.update(
        b"\0"
    )
    digest.update(
        exact_text.encode(
            "utf-8"
        )
    )

    return (
        "fiqh-unit:"
        + digest.hexdigest()[:24]
    )


@dataclass(
    frozen=True,
    slots=True,
)
class FiqhStructuralUnit:
    """
    Source-faithful legal evidence unit.

    The unit is NOT a fatwa and NOT an inferred ruling.

    Structural fields may only be populated from
    explicit source-derived material.

    Missing structure remains missing.
    """

    unit_id: str

    parent_passage_id: str

    source_id: str
    work_id: str
    work_title: str

    reference: str | None
    source_url: str | None

    source_version: str | None
    author_name: str | None
    institution: str | None
    publisher: str | None

    volume: str | None
    page: str | None

    madhhab: str | None

    issue: str | None

    exact_text: str

    ruling: str | None = None

    dalil: str | None = None

    wajh_al_dalala: str | None = None

    conditions: tuple[
        str,
        ...,
    ] = ()

    exceptions: tuple[
        str,
        ...,
    ] = ()

    disagreement: str | None = None

    parent_char_start: int | None = None
    parent_char_end: int | None = None

    @property
    def has_explicit_ruling(
        self,
    ) -> bool:
        return (
            self.ruling
            is not None
        )

    @property
    def has_explicit_dalil(
        self,
    ) -> bool:
        return (
            self.dalil
            is not None
        )

    @property
    def has_conditions(
        self,
    ) -> bool:
        return bool(
            self.conditions
        )

    @property
    def has_explicit_disagreement(
        self,
    ) -> bool:
        return (
            self.disagreement
            is not None
        )


class FiqhStructuralUnitBuilder:
    """
    Convert a governed projected Fiqh passage into a
    structural unit WITHOUT semantic invention.

    Trusted structure may come from:
    - source-authored section/chapter title;
    - governed metadata already extracted upstream;
    - exact source text.

    This builder never infers:
    - a ruling;
    - a proof;
    - wajh al-dalala;
    - conditions;
    - exceptions;
    - disagreement.
    """

    def from_projected_passage(
        self,
        passage: ScholarlyPassage,
    ) -> FiqhStructuralUnit:
        metadata = (
            passage.metadata
        )

        projection_kind = (
            metadata.get(
                "projection_kind"
            )
        )

        if (
            projection_kind
            != "fiqh_targeted_exact_slice"
        ):
            raise ValueError(
                "Fiqh structural units require a "
                "targeted governed projection."
            )

        parent_passage_id = (
            metadata.get(
                "parent_passage_id"
            )
        )

        if not parent_passage_id:
            raise ValueError(
                "Projected Fiqh passage is missing "
                "parent provenance."
            )

        exact_text = (
            passage.text
        )

        if not exact_text.strip():
            raise ValueError(
                "Fiqh structural unit cannot be empty."
            )

        madhhab = _clean_optional(
            metadata.get(
                "madhhab"
            )
        )

        issue = _clean_optional(
            passage.section_title
            or passage.chapter_title
        )

        ruling = (
            _require_exact_substring(
                parent=exact_text,
                child=metadata.get(
                    "fiqh_ruling"
                ),
                field_name="fiqh_ruling",
            )
        )

        dalil = (
            _require_exact_substring(
                parent=exact_text,
                child=metadata.get(
                    "fiqh_dalil"
                ),
                field_name="fiqh_dalil",
            )
        )

        wajh_al_dalala = (
            _require_exact_substring(
                parent=exact_text,
                child=metadata.get(
                    "fiqh_wajh_al_dalala"
                ),
                field_name=(
                    "fiqh_wajh_al_dalala"
                ),
            )
        )

        conditions = (
            _split_exact_values(
                parent=exact_text,
                value=metadata.get(
                    "fiqh_conditions"
                ),
                field_name=(
                    "fiqh_conditions"
                ),
            )
        )

        exceptions = (
            _split_exact_values(
                parent=exact_text,
                value=metadata.get(
                    "fiqh_exceptions"
                ),
                field_name=(
                    "fiqh_exceptions"
                ),
            )
        )

        disagreement = (
            _require_exact_substring(
                parent=exact_text,
                child=metadata.get(
                    "fiqh_disagreement"
                ),
                field_name=(
                    "fiqh_disagreement"
                ),
            )
        )

        start_raw = metadata.get(
            "projection_char_start"
        )
        end_raw = metadata.get(
            "projection_char_end"
        )

        start = (
            int(start_raw)
            if start_raw is not None
            else None
        )

        end = (
            int(end_raw)
            if end_raw is not None
            else None
        )

        if (
            start is not None
            and start < 0
        ):
            raise ValueError(
                "projection_char_start "
                "must be non-negative."
            )

        if (
            start is not None
            and end is not None
            and end <= start
        ):
            raise ValueError(
                "projection_char_end "
                "must be after start."
            )

        return FiqhStructuralUnit(
            unit_id=_stable_unit_id(
                parent_passage_id=(
                    parent_passage_id
                ),
                exact_text=exact_text,
            ),
            parent_passage_id=(
                parent_passage_id
            ),
            source_id=(
                passage.source_id
            ),
            work_id=(
                passage.work_id
            ),
            work_title=(
                passage.work_title
            ),
            reference=(
                passage.section_title
                or passage.chapter_title
            ),
            source_url=(
                passage.source_url
            ),
            source_version=(
                passage.source_version
            ),
            author_name=(
                passage.author_name
            ),
            institution=(
                passage.institution
            ),
            publisher=(
                passage.publisher
            ),
            volume=(
                passage.volume
            ),
            page=(
                passage.page
            ),
            madhhab=madhhab,
            issue=issue,
            exact_text=exact_text,
            ruling=ruling,
            dalil=dalil,
            wajh_al_dalala=(
                wajh_al_dalala
            ),
            conditions=conditions,
            exceptions=exceptions,
            disagreement=(
                disagreement
            ),
            parent_char_start=start,
            parent_char_end=end,
        )
