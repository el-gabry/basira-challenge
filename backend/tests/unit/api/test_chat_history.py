from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import basira.api.chat_history as chat_history


def test_chat_history_is_isolated_per_visitor(
    tmp_path,
    monkeypatch,
) -> None:
    database = (
        tmp_path
        / "chat.sqlite3"
    )

    monkeypatch.setenv(
        "BASIRA_CHAT_DB_PATH",
        str(database),
    )

    chat_history._INITIALIZED_PATHS.clear()

    app = FastAPI()
    app.include_router(
        chat_history.router
    )

    client = TestClient(app)

    visitor_a = (
        "visitor_A_1234567890"
    )

    visitor_b = (
        "visitor_B_1234567890"
    )

    headers_a = {
        "X-Basira-Visitor":
            visitor_a,
    }

    headers_b = {
        "X-Basira-Visitor":
            visitor_b,
    }

    empty_a = client.get(
        "/api/v1/chat/history",
        headers=headers_a,
    )

    empty_b = client.get(
        "/api/v1/chat/history",
        headers=headers_b,
    )

    assert empty_a.status_code == 200
    assert empty_b.status_code == 200

    assert (
        empty_a.json()["items"]
        == []
    )

    assert (
        empty_b.json()["items"]
        == []
    )

    saved = client.post(
        "/api/v1/chat/history",
        headers=headers_a,
        json={
            "question":
                "What does Ayat al-Kursi mean?",
            "language":
                "en",
            "response": {
                "request_id":
                    "request-a",
                "has_answer":
                    True,
            },
        },
    )

    assert saved.status_code == 200

    history_a = client.get(
        "/api/v1/chat/history",
        headers=headers_a,
    )

    history_b = client.get(
        "/api/v1/chat/history",
        headers=headers_b,
    )

    assert len(
        history_a.json()["items"]
    ) == 1

    assert (
        history_a.json()
        ["items"][0]
        ["question"]
        == "What does Ayat al-Kursi mean?"
    )

    assert (
        history_b.json()["items"]
        == []
    )


def test_invalid_visitor_id_is_rejected(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "BASIRA_CHAT_DB_PATH",
        str(
            tmp_path
            / "chat.sqlite3"
        ),
    )

    chat_history._INITIALIZED_PATHS.clear()

    app = FastAPI()
    app.include_router(
        chat_history.router
    )

    client = TestClient(app)

    result = client.get(
        "/api/v1/chat/history",
        headers={
            "X-Basira-Visitor":
                "too-short",
        },
    )

    assert result.status_code == 400
