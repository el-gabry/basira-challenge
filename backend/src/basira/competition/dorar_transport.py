from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
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

    def resolve_redirect_target(
        self,
        url: str,
    ) -> str:
        """
        Resolve exactly one redirect target without
        following it.

        This remains authority-neutral:
        - source URL is validated;
        - redirect is NOT followed;
        - Location is resolved;
        - target URL is validated again;
        - caller still owns domain/canonical-route
          validation.
        """

        requested_url = _validated_dorar_url(url)

        try:
            with self._client.stream(
                "GET",
                requested_url,
                follow_redirects=False,
            ) as response:
                if not response.is_redirect:
                    raise DorarTransportBlocked("redirect_expected")

                location = response.headers.get("location")

                if not location:
                    raise DorarTransportBlocked("redirect_location_missing")

                target = urljoin(
                    str(response.url),
                    location,
                )

                return _validated_dorar_url(target)

        except DorarTransportError:
            raise

        except httpx.HTTPError as exc:
            raise (DorarTransportUnavailable("network_error")) from exc

    def fetch(
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
