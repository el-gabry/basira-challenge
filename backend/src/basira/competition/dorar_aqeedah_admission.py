from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel

from basira.competition.dorar_aqeedah import (
    DorarAqeedahPassage,
    parse_dorar_aqeedah_passage,
)


class DorarAqeedahAdmissionError(
    ValueError
):
    pass


class DorarAqeedahEvidenceEnvelope(
    BaseModel
):
    source_id: str

    source_family: str

    provider: str

    runtime_eligibility: str

    passport_id: str

    canonical_url: str

    article_id: int

    response_sha256: str

    response_bytes: int

    adapter_contract: str

    passage: DorarAqeedahPassage

    quran_context_is_canonical_witness: bool = False

    independent_hadith_authentication: bool = False

    bibliographic_authority_promotion: bool = False

    generic_shamela_fallback_allowed: bool = False


def _load_json(
    path: Path,
) -> dict:

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _validate_canonical_url(
    *,
    url: str,
    path_regex: str,
) -> int:

    parsed = urlsplit(
        url
    )

    if parsed.scheme != "https":
        raise DorarAqeedahAdmissionError(
            "https_required"
        )

    if parsed.hostname != "dorar.net":
        raise DorarAqeedahAdmissionError(
            "exact_dorar_host_required"
        )

    if parsed.port is not None:
        raise DorarAqeedahAdmissionError(
            "custom_port_not_allowed"
        )

    if parsed.username or parsed.password:
        raise DorarAqeedahAdmissionError(
            "userinfo_not_allowed"
        )

    if parsed.query:
        raise DorarAqeedahAdmissionError(
            "query_not_allowed"
        )

    if parsed.fragment:
        raise DorarAqeedahAdmissionError(
            "fragment_not_allowed"
        )

    if not re.fullmatch(
        path_regex,
        parsed.path,
    ):
        raise DorarAqeedahAdmissionError(
            "noncanonical_aqeedah_article_path"
        )

    match = re.fullmatch(
        r"/aqeeda/([1-9][0-9]*)",
        parsed.path,
    )

    if match is None:
        raise DorarAqeedahAdmissionError(
            "positive_numeric_article_id_required"
        )

    return int(
        match.group(1)
    )


def admit_dorar_aqeedah_response(
    *,
    canonical_url: str,
    response_bytes: bytes,
    runtime_manifest_path: Path,
    passport_path: Path,
) -> DorarAqeedahEvidenceEnvelope:

    manifest = _load_json(
        runtime_manifest_path
    )

    passport = _load_json(
        passport_path
    )

    if (
        manifest[
            "runtime_eligibility"
        ]
        != "eligible"
    ):
        raise DorarAqeedahAdmissionError(
            "runtime_not_eligible"
        )

    if (
        passport[
            "runtime_eligibility"
        ]
        != "eligible"
    ):
        raise DorarAqeedahAdmissionError(
            "passport_not_runtime_eligible"
        )

    if (
        passport[
            "source_id"
        ]
        != manifest[
            "source_id"
        ]
    ):
        raise DorarAqeedahAdmissionError(
            "passport_source_mismatch"
        )

    if (
        passport[
            "adapter_contract"
        ]
        != manifest[
            "adapter_contract"
        ]
    ):
        raise DorarAqeedahAdmissionError(
            "adapter_contract_mismatch"
        )

    article_id = (
        _validate_canonical_url(
            url=canonical_url,
            path_regex=(
                manifest[
                    "canonical_path_regex"
                ]
            ),
        )
    )

    if not response_bytes:
        raise DorarAqeedahAdmissionError(
            "empty_response"
        )

    response_sha256 = (
        hashlib.sha256(
            response_bytes
        ).hexdigest()
    )

    baseline = manifest[
        "baseline_artifact"
    ]

    if (
        canonical_url
        == baseline[
            "url"
        ]
        and response_sha256
        != baseline[
            "sha256"
        ]
    ):
        raise DorarAqeedahAdmissionError(
            "baseline_artifact_drift"
        )

    html = response_bytes.decode(
        "utf-8",
        errors="replace",
    )

    passage = (
        parse_dorar_aqeedah_passage(
            html=html,
            canonical_url=canonical_url,
        )
    )

    routing = passage.routing

    if (
        routing.canonical_root_count
        != 1
    ):
        raise DorarAqeedahAdmissionError(
            "canonical_root_contract_failed"
        )

    if (
        routing.direct_article_body_count
        != 1
    ):
        raise DorarAqeedahAdmissionError(
            "article_body_contract_failed"
        )

    if (
        routing.provenance_violation_count
        != 0
    ):
        raise DorarAqeedahAdmissionError(
            "provenance_contract_failed"
        )

    boundaries = manifest[
        "hard_boundaries"
    ]

    if (
        boundaries[
            "quran_context_is_canonical_quran_witness"
        ]
        is not False
    ):
        raise DorarAqeedahAdmissionError(
            "unsafe_quran_boundary"
        )

    if (
        boundaries[
            "independent_hadith_authentication_allowed"
        ]
        is not False
    ):
        raise DorarAqeedahAdmissionError(
            "unsafe_hadith_boundary"
        )

    if (
        boundaries[
            "bibliographic_citation_promotes_aqeedah_authority"
        ]
        is not False
    ):
        raise DorarAqeedahAdmissionError(
            "unsafe_authority_boundary"
        )

    return DorarAqeedahEvidenceEnvelope(
        source_id=(
            manifest[
                "source_id"
            ]
        ),
        source_family=(
            manifest[
                "source_family"
            ]
        ),
        provider=(
            manifest[
                "provider"
            ]
        ),
        runtime_eligibility=(
            manifest[
                "runtime_eligibility"
            ]
        ),
        passport_id=(
            passport[
                "passport_id"
            ]
        ),
        canonical_url=canonical_url,
        article_id=article_id,
        response_sha256=(
            response_sha256
        ),
        response_bytes=(
            len(
                response_bytes
            )
        ),
        adapter_contract=(
            manifest[
                "adapter_contract"
            ]
        ),
        passage=passage,
    )
