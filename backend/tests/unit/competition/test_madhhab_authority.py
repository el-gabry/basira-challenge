from basira.competition.fiqh_policy import (
    FiqhSourceEligibility,
    Madhhab,
)
from basira.competition.madhhab_authority import (
    HybridBookDecision,
    MadhhabBookAuthorityClass,
    MadhhabBookAuthorityGate,
    MadhhabBookPassport,
    MadhhabBookRetrievalMode,
)


def test_verified_mutamad_governed_edition_is_allowed() -> None:
    result = MadhhabBookAuthorityGate().assess(
        MadhhabBookPassport(
            work_id="test:hanafi",
            canonical_title="كتاب",
            author="مؤلف",
            madhhab=Madhhab.HANAFI,
            authority_class=(
                MadhhabBookAuthorityClass
                .VERIFIED_MUTAMAD
            ),
            authority_evidence_ids=(
                "authority:evidence:1",
            ),
            exact_edition_governed=True,
            source_eligibility=(
                FiqhSourceEligibility.ELIGIBLE
            ),
        )
    )

    assert result.decision is HybridBookDecision.ALLOW
    assert result.may_call_mutamad is True
    assert result.may_use_as_primary_book_evidence is True


def test_dorar_reference_listing_does_not_prove_mutamad() -> None:
    result = MadhhabBookAuthorityGate().assess(
        MadhhabBookPassport(
            work_id="test:shafii",
            canonical_title="مرجع",
            author="مؤلف",
            madhhab=Madhhab.SHAFII,
            authority_class=(
                MadhhabBookAuthorityClass
                .DORAR_REFERENCE_LISTED
            ),
            authority_evidence_ids=(
                "dorar:refs:fiqhia",
            ),
            exact_edition_governed=True,
            source_eligibility=(
                FiqhSourceEligibility.ELIGIBLE
            ),
        )
    )

    assert (
        result.decision
        is HybridBookDecision.DISCOVERY_ONLY
    )

    assert result.may_call_mutamad is False


def test_recognized_reference_is_not_primary_in_mutamad_mode() -> None:
    result = MadhhabBookAuthorityGate().assess(
        MadhhabBookPassport(
            work_id="test:maliki",
            canonical_title="مرجع",
            author="مؤلف",
            madhhab=Madhhab.MALIKI,
            authority_class=(
                MadhhabBookAuthorityClass
                .VERIFIED_RECOGNIZED_REFERENCE
            ),
            authority_evidence_ids=(
                "authority:evidence:2",
            ),
            exact_edition_governed=True,
            source_eligibility=(
                FiqhSourceEligibility.ELIGIBLE
            ),
        ),
        mode=(
            MadhhabBookRetrievalMode.MUTAMAD_ONLY
        ),
    )

    assert (
        result.decision
        is HybridBookDecision.DISCOVERY_ONLY
    )

    assert result.may_call_mutamad is False


def test_ungoverned_edition_cannot_be_primary_evidence() -> None:
    result = MadhhabBookAuthorityGate().assess(
        MadhhabBookPassport(
            work_id="test:hanbali",
            canonical_title="كتاب",
            author="مؤلف",
            madhhab=Madhhab.HANBALI,
            authority_class=(
                MadhhabBookAuthorityClass
                .VERIFIED_MUTAMAD
            ),
            authority_evidence_ids=(
                "authority:evidence:3",
            ),
            exact_edition_governed=False,
            source_eligibility=(
                FiqhSourceEligibility
                .PENDING_AUDIT
            ),
        )
    )

    assert (
        result.decision
        is HybridBookDecision.DISCOVERY_ONLY
    )


def test_unknown_madhhab_is_blocked() -> None:
    result = MadhhabBookAuthorityGate().assess(
        MadhhabBookPassport(
            work_id="test:unknown",
            canonical_title="كتاب",
            author="مؤلف",
            madhhab=Madhhab.UNSPECIFIED,
            authority_class=(
                MadhhabBookAuthorityClass
                .VERIFIED_MUTAMAD
            ),
            authority_evidence_ids=(
                "authority:evidence:4",
            ),
            exact_edition_governed=True,
            source_eligibility=(
                FiqhSourceEligibility.ELIGIBLE
            ),
        )
    )

    assert result.decision is HybridBookDecision.BLOCK
