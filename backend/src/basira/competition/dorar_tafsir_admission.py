from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from basira.competition.dorar_tafsir import (
    DorarTafsirPassage,
    parse_dorar_tafsir_passage,
)
from basira.competition.tafsir_policy import (
    TafsirSourceEligibility,
    TafsirSourceFamily,
)


PASSPORT_RELATIVE_PATH = Path(
    "data/competition/passports/"
    "dorar-tafsir.json"
)


class DorarTafsirAdmissionDecision(StrEnum):
    ALLOW = "allow"

    DISCOVERY_ONLY = "discovery_only"

    BLOCK = "block"


class DorarTafsirPassport(BaseModel):
    passport_version: int

    passport_id: str

    provider: str

    source_family: TafsirSourceFamily

    runtime_eligibility: TafsirSourceEligibility

    runtime_scope: str

    canonical_origin: str

    canonical_path_contract: str

    adapter_contract: str

    characterization_result: str

    adversarial_audit_result: str

    characterization_commit: str

    adapter_audit_commit: str

    baseline_response_sha256: str

    artifact_sha256: dict[
        str,
        str,
    ] = Field(
        default_factory=dict
    )

    guardrails: dict[
        str,
        bool,
    ] = Field(
        default_factory=dict
    )

    limitations: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class DorarTafsirAdmissionAssessment(BaseModel):
    decision: DorarTafsirAdmissionDecision

    canonical_url: str | None = None

    surah_number: int | None = None

    passage_id: int | None = None

    reasons: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class DorarTafsirRuntimeEvidence(BaseModel):
    passport_id: str

    source_family: TafsirSourceFamily

    runtime_eligibility: TafsirSourceEligibility

    canonical_url: str

    response_sha256: str

    response_bytes: int

    adapter_contract: str

    passage: DorarTafsirPassage


_CANONICAL_PASSAGE_RE = re.compile(
    r"^/tafseer/"
    r"([1-9]\d*)/"
    r"([1-9]\d*)$"
)


_SURAH_DISCOVERY_RE = re.compile(
    r"^/tafseer/"
    r"([1-9]\d*)/?$"
)


_REQUIRED_FALSE_GUARDRAILS = {
    "quran_text_as_canonical_quran_witness",
    "independent_isnad_grading",
    "authenticity_from_frequency",
    "direct_fiqh_ruling_from_tafsir",
    "search_result_as_evidence",
    "surah_page_as_admitted_passage_evidence",
}


def sha256_file(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_dorar_tafsir_passport(
    path: Path,
) -> DorarTafsirPassport:

    raw = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return DorarTafsirPassport(
        **raw
    )


def passport_artifact_mismatches(
    passport: DorarTafsirPassport,
    *,
    repo_root: Path,
) -> tuple[str, ...]:

    mismatches: list[str] = []

    for relative_path, expected_sha in (
        passport.artifact_sha256.items()
    ):

        path = (
            repo_root
            / relative_path
        )

        if not path.is_file():
            mismatches.append(
                f"missing_artifact:{relative_path}"
            )
            continue

        actual_sha = sha256_file(
            path
        )

        if actual_sha != expected_sha:
            mismatches.append(
                f"artifact_hash_mismatch:{relative_path}"
            )

    return tuple(
        mismatches
    )


def _static_passport_failures(
    passport: DorarTafsirPassport,
) -> tuple[str, ...]:

    failures: list[str] = []

    if (
        passport.passport_id
        != "dorar-tafsir-v1"
    ):
        failures.append(
            "unexpected_passport_id"
        )

    if (
        passport.source_family
        is not TafsirSourceFamily
        .DORAR_TAFSIR
    ):
        failures.append(
            "wrong_source_family"
        )

    if (
        passport.runtime_eligibility
        is not TafsirSourceEligibility
        .ELIGIBLE
    ):
        failures.append(
            "source_not_runtime_eligible"
        )

    if (
        passport.runtime_scope
        != "canonical_passage_only"
    ):
        failures.append(
            "unexpected_runtime_scope"
        )

    if (
        passport.characterization_result
        != "PASS"
    ):
        failures.append(
            "characterization_not_pass"
        )

    if (
        passport.adversarial_audit_result
        != "PASS"
    ):
        failures.append(
            "adversarial_audit_not_pass"
        )

    if (
        len(
            passport.baseline_response_sha256
        )
        != 64
    ):
        failures.append(
            "baseline_response_hash_required"
        )

    for name in (
        _REQUIRED_FALSE_GUARDRAILS
    ):
        if (
            passport.guardrails.get(
                name
            )
            is not False
        ):
            failures.append(
                f"unsafe_guardrail:{name}"
            )

    if not passport.artifact_sha256:
        failures.append(
            "passport_artifact_hashes_required"
        )

    return tuple(
        failures
    )


class DorarTafsirRuntimeGate:
    """
    Controlled runtime admission for Dorar Tafsir.

    Discovery is broader than evidence use.

    Only canonical passage pages are admitted as runtime
    Tafsir evidence under this V1 contract.
    """

    def __init__(
        self,
        *,
        passport: DorarTafsirPassport,
        artifact_mismatches: tuple[
            str,
            ...
        ] = (),
    ) -> None:

        self.passport = passport

        self.artifact_mismatches = (
            artifact_mismatches
        )

        self.static_failures = (
            _static_passport_failures(
                passport
            )
        )

    @classmethod
    def from_repo(
        cls,
        repo_root: Path,
    ) -> "DorarTafsirRuntimeGate":

        passport = (
            load_dorar_tafsir_passport(
                repo_root
                / PASSPORT_RELATIVE_PATH
            )
        )

        mismatches = (
            passport_artifact_mismatches(
                passport,
                repo_root=repo_root,
            )
        )

        return cls(
            passport=passport,
            artifact_mismatches=mismatches,
        )

    def assess(
        self,
        url: str,
    ) -> DorarTafsirAdmissionAssessment:

        failures = list(
            self.static_failures
        )

        failures.extend(
            self.artifact_mismatches
        )

        if failures:
            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision.BLOCK
                ),
                reasons=tuple(
                    failures
                ),
            )

        try:
            parts = urlsplit(
                url
            )
        except ValueError:
            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision.BLOCK
                ),
                reasons=(
                    "invalid_url",
                ),
            )

        # Exact transport/origin contract.
        if parts.scheme != "https":
            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision.BLOCK
                ),
                reasons=(
                    "https_required",
                ),
            )

        # This intentionally rejects:
        # - subdomains
        # - explicit ports
        # - userinfo
        if parts.netloc != "dorar.net":
            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision.BLOCK
                ),
                reasons=(
                    "exact_dorar_host_required",
                ),
            )

        if parts.query:
            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision.BLOCK
                ),
                reasons=(
                    "query_not_allowed",
                ),
            )

        if parts.fragment:
            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision.BLOCK
                ),
                reasons=(
                    "fragment_not_allowed",
                ),
            )

        if (
            "%"
            in parts.path
            or "\\"
            in parts.path
            or "//"
            in parts.path
        ):
            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision.BLOCK
                ),
                reasons=(
                    "noncanonical_path_encoding",
                ),
            )

        match = (
            _CANONICAL_PASSAGE_RE
            .fullmatch(
                parts.path
            )
        )

        if match:

            surah_number = int(
                match.group(1)
            )

            passage_id = int(
                match.group(2)
            )

            if not (
                1
                <= surah_number
                <= 114
            ):
                return DorarTafsirAdmissionAssessment(
                    decision=(
                        DorarTafsirAdmissionDecision.BLOCK
                    ),
                    reasons=(
                        "invalid_surah_number",
                    ),
                )

            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision.ALLOW
                ),
                canonical_url=url,
                surah_number=surah_number,
                passage_id=passage_id,
                reasons=(
                    "official_dorar_tafsir_family",
                    "canonical_passage_scope",
                    "passport_verified",
                ),
            )

        discovery_match = (
            _SURAH_DISCOVERY_RE
            .fullmatch(
                parts.path
            )
        )

        if discovery_match:

            surah_number = int(
                discovery_match.group(1)
            )

            if not (
                1
                <= surah_number
                <= 114
            ):
                return DorarTafsirAdmissionAssessment(
                    decision=(
                        DorarTafsirAdmissionDecision.BLOCK
                    ),
                    reasons=(
                        "invalid_surah_number",
                    ),
                )

            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision
                    .DISCOVERY_ONLY
                ),
                surah_number=surah_number,
                reasons=(
                    "surah_page_not_admitted_in_v1",
                ),
            )

        if parts.path in {
            "/tafseer",
            "/tafseer/",
            "/refs/tafseer",
            "/refs/tafseer/",
        }:
            return DorarTafsirAdmissionAssessment(
                decision=(
                    DorarTafsirAdmissionDecision
                    .DISCOVERY_ONLY
                ),
                reasons=(
                    "discovery_surface_not_runtime_evidence",
                ),
            )

        return DorarTafsirAdmissionAssessment(
            decision=(
                DorarTafsirAdmissionDecision.BLOCK
            ),
            reasons=(
                "outside_admitted_tafsir_scope",
            ),
        )

    def admit(
        self,
        *,
        html: str | bytes,
        canonical_url: str,
    ) -> DorarTafsirRuntimeEvidence:

        assessment = self.assess(
            canonical_url
        )

        if (
            assessment.decision
            is not DorarTafsirAdmissionDecision.ALLOW
        ):
            raise ValueError(
                "Dorar Tafsir runtime admission blocked: "
                + ",".join(
                    assessment.reasons
                )
            )

        if isinstance(
            html,
            bytes,
        ):
            raw = html

            html_text = raw.decode(
                "utf-8",
                errors="replace",
            )

        else:
            html_text = html

            raw = html.encode(
                "utf-8"
            )

        passage = (
            parse_dorar_tafsir_passage(
                html=html_text,
                canonical_url=canonical_url,
            )
        )

        return DorarTafsirRuntimeEvidence(
            passport_id=(
                self.passport.passport_id
            ),
            source_family=(
                TafsirSourceFamily.DORAR_TAFSIR
            ),
            runtime_eligibility=(
                TafsirSourceEligibility.ELIGIBLE
            ),
            canonical_url=canonical_url,
            response_sha256=(
                hashlib.sha256(
                    raw
                ).hexdigest()
            ),
            response_bytes=len(
                raw
            ),
            adapter_contract=(
                self.passport.adapter_contract
            ),
            passage=passage,
        )
