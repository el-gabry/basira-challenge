from __future__ import annotations

import basira.api.app as app_module


def test_public_query_service_is_request_scoped(
    monkeypatch,
) -> None:
    created: list[object] = []

    class FakeService:
        pass

    def builder() -> FakeService:
        service = FakeService()
        created.append(service)
        return service

    monkeypatch.setattr(
        app_module,
        "build_default_query_service",
        builder,
    )

    first = app_module.get_query_service()
    second = app_module.get_query_service()

    assert len(created) == 2
    assert first is not second


def test_query_keeps_getter_seam() -> None:
    assert (
        "get_query_service"
        in app_module.query.__code__.co_names
    )


def test_evidence_detail_keeps_getter_seam() -> None:
    assert (
        "get_query_service"
        in app_module.evidence_detail.__code__.co_names
    )
