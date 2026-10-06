from basira.competition.hadith_policy import (
    HadithAttestation,
    HadithAuthorityClass,
    HadithEvidenceCandidate,
    HadithEvidenceDecision,
    HadithVerificationAuthority,
    HadithVerificationState,
    OfficialHadithPolicy,
)


def policy() -> OfficialHadithPolicy:
    return OfficialHadithPolicy()


def test_sahih_bukhari_uses_primary_path() -> None:
    result = policy().assess(
        HadithEvidenceCandidate(
            hadith_text=(
                "إنما الأعمال بالنيات"
            ),
            claimed_collection=(
                "صحيح البخاري"
            ),
            collection_reference="1",
            narrator="عمر بن الخطاب",
            governed_canonical_source=True,
        )
    )

    assert (
        result.authority_class
        is HadithAuthorityClass
        .SAHIHAIN_PRIMARY
    )

    assert (
        result.decision
        is HadithEvidenceDecision.USABLE
    )

    assert (
        result.verification_state
        is HadithVerificationState
        .SAHIHAIN_SOURCE_VERIFIED
    )


def test_other_sunnah_with_dorar_grading_is_usable() -> None:
    result = policy().assess(
        HadithEvidenceCandidate(
            hadith_text="نص حديث",
            claimed_collection="سنن أبي داود",
            collection_reference="1234",
            narrator="راو",
            attestations=(
                HadithAttestation(
                    verification_authority=(
                        HadithVerificationAuthority
                        .DORAR
                    ),
                    muhaddith="الألباني",
                    verdict="صحيح",
                    reference="dorar:123",
                ),
            ),
        )
    )

    assert (
        result.decision
        is HadithEvidenceDecision
        .USABLE_WITH_ATTRIBUTED_GRADINGS
    )

    assert (
        result.verification_state
        is HadithVerificationState
        .VERIFIED_WITH_ATTRIBUTED_GRADING
    )


def test_unattributed_hadith_is_blocked() -> None:
    result = policy().assess(
        HadithEvidenceCandidate(
            hadith_text=(
                "قال رسول الله كذا"
            ),
        )
    )

    assert (
        result.decision
        is HadithEvidenceDecision
        .NOT_USABLE_AS_HADITH_EVIDENCE
    )

    assert (
        result.verification_state
        is HadithVerificationState
        .MISSING_ATTRIBUTION
    )


def test_other_sunnah_without_verification_retrieves_more() -> None:
    result = policy().assess(
        HadithEvidenceCandidate(
            hadith_text="نص حديث",
            claimed_collection="سنن الترمذي",
            collection_reference="100",
        )
    )

    assert (
        result.decision
        is HadithEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        result.verification_state
        is HadithVerificationState
        .UNVERIFIED
    )


def test_conflicting_gradings_are_preserved() -> None:
    result = policy().assess(
        HadithEvidenceCandidate(
            hadith_text="نص حديث",
            claimed_collection="كتاب من كتب السنة",
            collection_reference="50",
            attestations=(
                HadithAttestation(
                    verification_authority=(
                        HadithVerificationAuthority
                        .DORAR
                    ),
                    muhaddith="محدث أ",
                    verdict="صحيح",
                ),
                HadithAttestation(
                    verification_authority=(
                        HadithVerificationAuthority
                        .DORAR
                    ),
                    muhaddith="محدث ب",
                    verdict="ضعيف",
                ),
            ),
        )
    )

    assert (
        result.verification_state
        is HadithVerificationState
        .CONFLICTING_ATTRIBUTED_GRADINGS
    )

    assert (
        result.decision
        is HadithEvidenceDecision
        .USABLE_WITH_ATTRIBUTED_GRADINGS
    )

    assert result.majority_vote_allowed is False
    assert (
        result.consensus_inference_allowed
        is False
    )


def test_zero_hits_does_not_mean_no_hadith_exists() -> None:
    result = policy().assess(
        HadithEvidenceCandidate(
            hadith_text="نص مطلوب التحقق منه",
            claimed_collection="سنن أخرى",
            collection_reference="unknown",
            no_hits_for_query=True,
        )
    )

    assert (
        result.verification_state
        is HadithVerificationState
        .NO_HITS_FOR_QUERY
    )

    assert (
        result.decision
        is HadithEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        "zero_hits_do_not_prove_nonexistence"
        in result.reasons
    )


def test_hadith_authenticity_does_not_disable_semantic_check() -> None:
    result = policy().assess(
        HadithEvidenceCandidate(
            hadith_text="حديث صحيح",
            claimed_collection="صحيح مسلم",
            collection_reference="123",
            governed_canonical_source=True,
        )
    )

    assert (
        result.requires_claim_evidence_check
        is True
    )
