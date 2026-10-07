from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin, urlsplit

import httpx

_DORAR_HOST = "dorar.net"

_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "text/plain",
        "application/json",
        "application/ld+json",
    }
)


class DorarTransportError(RuntimeError):
    pass


class DorarTransportBlocked(DorarTransportError):
    """
    Request or response violates the transport
    security/governance boundary.
    """

    pass


class DorarTransportUnavailable(DorarTransportError):
    """
    The governed source could not be obtained.

    This is deliberately different from a valid
    retrieval returning zero relevant records.
    """

    pass


class DorarFetchPurpose(StrEnum):
    DISCOVERY = "discovery"
    EVIDENCE = "evidence"


@dataclass(
    frozen=True,
    slots=True,
)
class DorarFetchedResponse:
    """
    Raw source response.

    This object is NOT religious evidence.

    Domain-specific admission/policy code must inspect
    and admit it before anything may enter a trusted
    evidence lane.
    """

    requested_url: str
    final_url: str
    purpose: DorarFetchPurpose
    status_code: int
    content_type: str
    body: bytes
    response_sha256: str


@dataclass(
    frozen=True,
    slots=True,
)
class DorarDiscoveryHit:
    """
    Discovery candidate only.

    Discovery can propose where evidence may exist.
    It cannot grant evidentiary authority.
    """

    canonical_url: str
    title: str | None = None
    snippet: str | None = None


class DorarDiscoveryProvider(Protocol):
    def search(
        self,
        query: str,
        *,
        limit: int,
    ) -> tuple[
        DorarDiscoveryHit,
        ...,
    ]: ...


def _validated_dorar_url(
    value: str,
) -> str:
    value = value.strip()

    if not value:
        raise DorarTransportBlocked("blank_url")

    parsed = urlsplit(value)

    if parsed.scheme != "https":
        raise DorarTransportBlocked("https_required")

    if parsed.hostname != _DORAR_HOST:
        raise DorarTransportBlocked("unexpected_host")

    if parsed.username is not None or parsed.password is not None:
        raise DorarTransportBlocked("credentials_not_allowed")

    if parsed.fragment:
        raise DorarTransportBlocked("fragment_not_allowed")

    return value


def _normalized_content_type(
    raw: str | None,
) -> str:
    if raw is None:
        raise DorarTransportBlocked("missing_content_type")

    value = (
        raw.split(
            ";",
            maxsplit=1,
        )[0]
        .strip()
        .lower()
    )

    if value not in _ALLOWED_CONTENT_TYPES:
        raise DorarTransportBlocked("unsupported_content_type:" + value)

    return value


class DorarHttpTransport:
    """
    Authority-neutral Dorar HTTP transport.

    Security boundary:
    - HTTPS only;
    - dorar.net only;
    - redirects are not followed;
    - bounded response size;
    - bounded content types;
    - exact response hash preserved.

    It NEVER:
    - selects a religious domain;
    - decides authority;
    - parses religious claims;
    - creates EvidenceNodes;
    - turns discovery results into evidence.
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 12.0,
        max_response_bytes: int = (2 * 1024 * 1024),
        cache_root: Path | str | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")

        self._owns_client = client is None

        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": ("Basira/competition-retrieval")},
        )

        self._max_response_bytes = max_response_bytes

        configured_cache_root = (
            cache_root
            if cache_root is not None
            else os.getenv("BASIRA_DORAR_CACHE_ROOT")
        )

        self._cache_root = (
            Path(configured_cache_root).expanduser().resolve()
            if configured_cache_root
            else None
        )

    def close(
        self,
    ) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(
        self,
    ) -> DorarHttpTransport:
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        del (
            exc_type,
            exc,
            traceback,
        )

        self.close()

    def _cached_redirect_target(
        self,
        requested_url: str,
    ) -> str | None:
        """
        Return one exact cached redirect mapping.

        Security invariants:
        - exact requested URL match only;
        - exactly one mapping;
        - target must still be a valid Dorar URL;
        - target string is SHA256-bound;
        - no heuristic redirect reconstruction.
        """

        requested_url = (
            _validated_dorar_url(
                requested_url
            )
        )

        root = self._cache_root

        if root is None:
            return None

        manifest_path = (
            root / "manifest.json"
        )

        try:
            import json

            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

        except FileNotFoundError:
            return None

        except Exception as exc:
            raise DorarTransportBlocked(
                "cache_manifest_invalid"
            ) from exc

        if not isinstance(
            manifest,
            dict,
        ):
            raise DorarTransportBlocked(
                "cache_manifest_invalid"
            )

        redirects = manifest.get(
            "redirects",
            [],
        )

        if not isinstance(
            redirects,
            list,
        ):
            raise DorarTransportBlocked(
                "cache_redirects_invalid"
            )

        matches = []

        for entry in redirects:
            if not isinstance(
                entry,
                dict,
            ):
                raise DorarTransportBlocked(
                    "cache_redirect_entry_invalid"
                )

            if (
                entry.get(
                    "requested_url"
                )
                == requested_url
            ):
                matches.append(
                    entry
                )

        if not matches:
            return None

        if len(matches) != 1:
            raise DorarTransportBlocked(
                "cache_redirect_ambiguous"
            )

        entry = matches[0]

        raw_target = entry.get(
            "target_url"
        )

        if not isinstance(
            raw_target,
            str,
        ):
            raise DorarTransportBlocked(
                "cache_redirect_target_invalid"
            )

        target = (
            _validated_dorar_url(
                raw_target
            )
        )

        expected_sha256 = entry.get(
            "target_sha256"
        )

        if (
            not isinstance(
                expected_sha256,
                str,
            )
            or len(
                expected_sha256
            )
            != 64
        ):
            raise DorarTransportBlocked(
                "cache_redirect_sha256_invalid"
            )

        digest = sha256(
            target.encode(
                "utf-8"
            )
        ).hexdigest()

        if digest != expected_sha256:
            raise DorarTransportBlocked(
                "cache_redirect_hash_mismatch"
            )

        return target

    def _resolve_redirect_target_live(
        self,
        requested_url: str,
    ) -> str:
        """
        Probe exactly one live redirect.

        Availability failures may later use an exact
        cached mapping. Protocol/security failures may not.
        """

        requested_url = (
            _validated_dorar_url(
                requested_url
            )
        )

        try:
            with self._client.stream(
                "GET",
                requested_url,
                follow_redirects=False,
            ) as response:
                if response.is_redirect:
                    location = (
                        response.headers.get(
                            "location"
                        )
                    )

                    if not location:
                        raise (
                            DorarTransportBlocked(
                                "redirect_location_missing"
                            )
                        )

                    target = urljoin(
                        str(
                            response.url
                        ),
                        location,
                    )

                    return (
                        _validated_dorar_url(
                            target
                        )
                    )

                # Cloudflare / network-side
                # availability responses.
                if response.status_code in {
                    403,
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    raise (
                        DorarTransportUnavailable(
                            "http_status:"
                            + str(
                                response.status_code
                            )
                        )
                    )

                # A successful non-redirect response
                # violates the short-URL contract.
                raise DorarTransportBlocked(
                    "redirect_expected"
                )

        except DorarTransportError:
            raise

        except httpx.HTTPError as exc:
            raise (
                DorarTransportUnavailable(
                    "network_error"
                )
            ) from exc

    def resolve_redirect_target(
        self,
        url: str,
    ) -> str:
        """
        Prefer the live redirect probe.

        Only an availability failure may use an exact,
        manifest-bound, SHA256-checked redirect mapping.
        """

        requested_url = (
            _validated_dorar_url(
                url
            )
        )

        try:
            return (
                self
                ._resolve_redirect_target_live(
                    requested_url
                )
            )

        except DorarTransportUnavailable:
            cached = (
                self
                ._cached_redirect_target(
                    requested_url
                )
            )

            if cached is None:
                raise

            return cached

    def _fetch_live(
        self,
        url: str,
        *,
        purpose: DorarFetchPurpose,
    ) -> DorarFetchedResponse:
        requested_url = _validated_dorar_url(url)

        try:
            with self._client.stream(
                "GET",
                requested_url,
                follow_redirects=False,
            ) as response:
                final_url = _validated_dorar_url(str(response.url))

                if response.is_redirect:
                    raise DorarTransportBlocked("redirect_not_allowed")

                if response.status_code != 200:
                    raise (
                        DorarTransportUnavailable(f"http_status:{response.status_code}")
                    )

                content_type = _normalized_content_type(
                    response.headers.get("content-type")
                )

                chunks: list[bytes] = []
                total = 0

                for chunk in response.iter_bytes():
                    total += len(chunk)

                    if total > self._max_response_bytes:
                        raise (DorarTransportBlocked("response_too_large"))

                    chunks.append(chunk)

                body = b"".join(chunks)

        except DorarTransportError:
            raise

        except httpx.HTTPError as exc:
            raise (DorarTransportUnavailable("network_error")) from exc

        digest = sha256(body).hexdigest()

        return DorarFetchedResponse(
            requested_url=(requested_url),
            final_url=final_url,
            purpose=purpose,
            status_code=200,
            content_type=content_type,
            body=body,
            response_sha256=digest,
        )

    def _cached_response(
        self,
        requested_url: str,
        *,
        purpose: DorarFetchPurpose,
    ) -> DorarFetchedResponse | None:
        """
        Read one exact, hash-bound official response.

        The cache is transport continuity only.
        It grants no religious authority and cannot
        admit an URL or purpose absent from its manifest.
        """

        root = self._cache_root

        if root is None:
            return None

        manifest_path = root / "manifest.json"

        try:
            raw_manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8",
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise DorarTransportBlocked(
                "cache_manifest_invalid"
            ) from exc

        if not isinstance(raw_manifest, dict):
            raise DorarTransportBlocked(
                "cache_manifest_not_object"
            )

        fetches = raw_manifest.get("fetches")

        if not isinstance(fetches, list):
            raise DorarTransportBlocked(
                "cache_fetches_invalid"
            )

        matches = [
            item
            for item in fetches
            if (
                isinstance(item, dict)
                and item.get("requested_url")
                == requested_url
                and item.get("purpose")
                == purpose.value
            )
        ]

        if not matches:
            return None

        if len(matches) != 1:
            raise DorarTransportBlocked(
                "cache_entry_ambiguous"
            )

        entry = matches[0]

        if entry.get("status_code") != 200:
            raise DorarTransportBlocked(
                "cache_status_not_200"
            )

        raw_final_url = entry.get("final_url")

        if not isinstance(
            raw_final_url,
            str,
        ):
            raise DorarTransportBlocked(
                "cache_final_url_invalid"
            )

        final_url = _validated_dorar_url(
            raw_final_url
        )

        # fetch() never follows redirects.
        # Cached responses must preserve that invariant.
        if final_url != requested_url:
            raise DorarTransportBlocked(
                "cache_final_url_mismatch"
            )

        raw_content_type = entry.get(
            "content_type"
        )

        if not isinstance(
            raw_content_type,
            str,
        ):
            raise DorarTransportBlocked(
                "cache_content_type_invalid"
            )

        content_type = _normalized_content_type(
            raw_content_type
        )

        raw_body_path = entry.get(
            "body_path"
        )

        if (
            not isinstance(
                raw_body_path,
                str,
            )
            or not raw_body_path.strip()
        ):
            raise DorarTransportBlocked(
                "cache_body_path_invalid"
            )

        body_path = (
            root
            / raw_body_path
        ).resolve()

        try:
            body_path.relative_to(root)
        except ValueError as exc:
            raise DorarTransportBlocked(
                "cache_body_path_escape"
            ) from exc

        try:
            body = body_path.read_bytes()
        except OSError as exc:
            raise DorarTransportBlocked(
                "cache_body_unavailable"
            ) from exc

        if len(body) > self._max_response_bytes:
            raise DorarTransportBlocked(
                "response_too_large"
            )

        expected_bytes = entry.get(
            "response_bytes"
        )

        if (
            not isinstance(
                expected_bytes,
                int,
            )
            or expected_bytes != len(body)
        ):
            raise DorarTransportBlocked(
                "cache_response_size_mismatch"
            )

        expected_sha256 = entry.get(
            "response_sha256"
        )

        if (
            not isinstance(
                expected_sha256,
                str,
            )
            or len(expected_sha256) != 64
        ):
            raise DorarTransportBlocked(
                "cache_sha256_invalid"
            )

        digest = sha256(body).hexdigest()

        if digest != expected_sha256:
            raise DorarTransportBlocked(
                "cache_hash_mismatch"
            )

        return DorarFetchedResponse(
            requested_url=requested_url,
            final_url=final_url,
            purpose=purpose,
            status_code=200,
            content_type=content_type,
            body=body,
            response_sha256=digest,
        )

    def fetch(
        self,
        url: str,
        *,
        purpose: DorarFetchPurpose,
    ) -> DorarFetchedResponse:
        """
        Prefer live Dorar.

        An explicitly configured cache may provide an
        exact SHA256-bound official response only when
        the live source is unavailable.

        Policy/admission remains downstream and unchanged.
        """

        requested_url = _validated_dorar_url(
            url
        )

        try:
            return self._fetch_live(
                requested_url,
                purpose=purpose,
            )

        except DorarTransportUnavailable:
            cached = self._cached_response(
                requested_url,
                purpose=purpose,
            )

            if cached is None:
                raise

            return cached
