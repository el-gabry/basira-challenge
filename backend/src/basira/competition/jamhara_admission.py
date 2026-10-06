from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(
    __file__
).resolve().parents[3]

SOURCE_ID = "jamhara-live-v1"

PASSPORT = (
    ROOT
    / "data"
    / "competition"
    / "passports"
    / "jamhara.json"
)

RUNTIME_MANIFEST = (
    ROOT
    / "data"
    / "competition"
    / "manifests"
    / "terminology"
    / "jamhara-runtime-v1.json"
)

REGISTRY = (
    ROOT
    / "data"
    / "competition"
    / "sources"
    / "terminology"
    / "terminology_source_registry.json"
)


@dataclass(
    frozen=True
)
class JamharaRuntimeState:
    source_id: str
    eligible: bool
    source_identity_verified: bool
    implementation_governed: bool
    terminology_only: bool
    cross_domain_primary_evidence: bool
    machine_translation_may_replace_governed_term: bool
    snapshot_required: bool

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.eligible
            and self.source_identity_verified
            and self.implementation_governed
            and self.terminology_only
            and not (
                self.cross_domain_primary_evidence
            )
            and not (
                self.machine_translation_may_replace_governed_term
            )
            and not self.snapshot_required
        )


def _load_json(
    path: Path,
) -> dict:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise RuntimeError(
            f"expected JSON object: {path}"
        )

    return value


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def _verify_integrity_bundle(
    bundle: object,
    *,
    label: str,
) -> None:
    if not isinstance(
        bundle,
        dict,
    ):
        raise RuntimeError(
            f"{label} integrity bundle missing"
        )

    for name, spec in bundle.items():
        if not isinstance(
            spec,
            dict,
        ):
            raise RuntimeError(
                f"{label} integrity spec invalid: "
                f"{name}"
            )

        relative = spec.get(
            "path"
        )

        expected = spec.get(
            "sha256"
        )

        if not isinstance(
            relative,
            str,
        ):
            raise RuntimeError(
                f"{label} path missing: {name}"
            )

        if not isinstance(
            expected,
            str,
        ):
            raise RuntimeError(
                f"{label} hash missing: {name}"
            )

        path = ROOT / relative

        if not path.is_file():
            raise RuntimeError(
                f"{label} artifact missing: "
                f"{relative}"
            )

        actual = _sha256(
            path
        )

        if actual != expected:
            raise RuntimeError(
                f"{label} integrity mismatch: "
                f"{relative}"
            )


def load_jamhara_runtime_state(
) -> JamharaRuntimeState:
    """
    Validate Jamhara's governed live-runtime chain.

    Unlike frozen-corpus sources, Jamhara admission
    pins the official origin, route contract, source
    authority boundary, deterministic extractor and
    resolver implementations.

    The background snapshot is explicitly not a
    prerequisite for live terminology admission.
    """

    passport = _load_json(
        PASSPORT
    )

    runtime = _load_json(
        RUNTIME_MANIFEST
    )

    registry = _load_json(
        REGISTRY
    )

    if (
        runtime.get("source_id")
        != SOURCE_ID
    ):
        raise RuntimeError(
            "unexpected Jamhara runtime source id"
        )

    if (
        runtime.get(
            "runtime_eligibility"
        )
        != "eligible"
    ):
        raise RuntimeError(
            "Jamhara runtime is not eligible"
        )

    if (
        passport.get(
            "runtime_source_id"
        )
        != SOURCE_ID
    ):
        raise RuntimeError(
            "Jamhara passport source id mismatch"
        )

    if (
        passport.get(
            "runtime_admission"
        )
        != "GOVERNED_TERMINOLOGY_RUNTIME"
    ):
        raise RuntimeError(
            "Jamhara passport is not "
            "runtime admitted"
        )

    if (
        runtime.get("passport_id")
        != passport.get("passport_id")
    ):
        raise RuntimeError(
            "Jamhara passport mismatch"
        )

    expected_family = (
        "AL_JAMHARA_ISLAMIC_TERMINOLOGY"
    )

    if (
        passport.get("source_family")
        != expected_family
        or runtime.get("source_family")
        != expected_family
    ):
        raise RuntimeError(
            "unexpected Jamhara source family"
        )

    if (
        passport.get("domain")
        != "translation_terminology"
        or runtime.get("domain")
        != "translation_terminology"
    ):
        raise RuntimeError(
            "unexpected Jamhara domain"
        )

    expected_role = (
        "PRIMARY_TERMINOLOGY_SOURCE"
    )

    if (
        passport.get("authority_role")
        != expected_role
        or runtime.get("runtime_role")
        != expected_role
    ):
        raise RuntimeError(
            "unexpected Jamhara authority role"
        )

    expected_origin = (
        "https://islamic-content.com"
    )

    if (
        passport.get("official_origin")
        != expected_origin
        or runtime.get("official_origin")
        != expected_origin
    ):
        raise RuntimeError(
            "Jamhara official origin mismatch"
        )

    expected_route = (
        "https://islamic-content.com/"
        "dictionary/word/{word_id}/{language}"
    )

    if (
        passport.get("route_template")
        != expected_route
        or runtime.get("route_template")
        != expected_route
    ):
        raise RuntimeError(
            "Jamhara route contract mismatch"
        )

    implementation = passport.get(
        "implementation_integrity"
    )

    if (
        implementation
        != runtime.get(
            "implementation_integrity"
        )
    ):
        raise RuntimeError(
            "Jamhara implementation integrity "
            "contracts disagree"
        )

    policy = passport.get(
        "policy_integrity"
    )

    if (
        policy
        != runtime.get(
            "policy_integrity"
        )
    ):
        raise RuntimeError(
            "Jamhara policy integrity "
            "contracts disagree"
        )

    sources = registry.get(
        "sources"
    )

    if not isinstance(
        sources,
        list,
    ):
        raise RuntimeError(
            "Jamhara registry sources missing"
        )

    source = next(
        (
            item
            for item in sources
            if (
                isinstance(
                    item,
                    dict,
                )
                and item.get(
                    "source_id"
                )
                == SOURCE_ID
            )
        ),
        None,
    )

    if source is None:
        raise RuntimeError(
            "Jamhara registry source missing"
        )

    for key, expected in (
        (
            "runtime_eligibility",
            "eligible",
        ),
        (
            "source_family",
            expected_family,
        ),
        (
            "domain",
            "translation_terminology",
        ),
        (
            "authority_role",
            expected_role,
        ),
        (
            "official_origin",
            expected_origin,
        ),
        (
            "route_template",
            expected_route,
        ),
    ):
        if source.get(
            key
        ) != expected:
            raise RuntimeError(
                "Jamhara registry mismatch: "
                f"{key}"
            )

    if (
        source.get(
            "implementation_integrity"
        )
        != implementation
    ):
        raise RuntimeError(
            "Jamhara registry implementation "
            "integrity mismatch"
        )

    if (
        source.get(
            "policy_integrity"
        )
        != policy
    ):
        raise RuntimeError(
            "Jamhara registry policy "
            "integrity mismatch"
        )

    _verify_integrity_bundle(
        implementation,
        label="implementation",
    )

    _verify_integrity_bundle(
        policy,
        label="policy",
    )

    translation = passport.get(
        "translation_policy",
        {},
    )

    if (
        translation.get(
            "approved_terminology_precedes_machine_translation"
        )
        is not True
    ):
        raise RuntimeError(
            "Jamhara terminology priority "
            "contract missing"
        )

    if (
        translation.get(
            "machine_translation_may_replace_governed_term"
        )
        is not False
    ):
        raise RuntimeError(
            "unsafe Jamhara machine-translation "
            "replacement policy"
        )

    boundary = passport.get(
        "authority_boundary",
        {},
    )

    if (
        boundary.get(
            "terminology_authority"
        )
        is not True
    ):
        raise RuntimeError(
            "Jamhara terminology authority missing"
        )

    if (
        boundary.get(
            "universal_primary_evidence"
        )
        is not False
        or boundary.get(
            "cross_domain_primary_evidence"
        )
        is not False
    ):
        raise RuntimeError(
            "Jamhara evidentiary authority "
            "is over-broad"
        )

    runtime_delivery = passport.get(
        "runtime_delivery",
        {},
    )

    if (
        runtime_delivery.get(
            "cache_is_trust_anchor"
        )
        is not False
    ):
        raise RuntimeError(
            "Jamhara cache cannot be a trust anchor"
        )

    if (
        runtime_delivery.get(
            "cross_origin_redirects_allowed"
        )
        is not False
    ):
        raise RuntimeError(
            "Jamhara cross-origin redirects "
            "must remain prohibited"
        )

    snapshot = passport.get(
        "snapshot_policy",
        {},
    )

    snapshot_required = snapshot.get(
        "required_for_runtime"
    )

    if snapshot_required is not False:
        raise RuntimeError(
            "Jamhara live runtime must not "
            "pretend snapshot completion is required"
        )

    if (
        runtime.get(
            "snapshot_required"
        )
        is not False
    ):
        raise RuntimeError(
            "Jamhara runtime snapshot contract "
            "disagrees with passport"
        )

    return JamharaRuntimeState(
        source_id=SOURCE_ID,
        eligible=True,
        source_identity_verified=True,
        implementation_governed=True,
        terminology_only=True,
        cross_domain_primary_evidence=False,
        machine_translation_may_replace_governed_term=False,
        snapshot_required=False,
    )
