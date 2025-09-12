import json
from typing import Any, Dict

import pytest

from lamina import Request, lamina


@pytest.fixture(autouse=True)
def clear_lamina_env(monkeypatch: pytest.MonkeyPatch):
    # Ensure a clean environment for each test
    for key in (
        "LAMINA_PRE_PARSE",
        "LAMINA_PRE_EXECUTE",
        "LAMINA_POS_EXECUTE",
        "LAMINA_PRE_RESPONSE",
    ):
        monkeypatch.delenv(key, raising=False)


def _event_with_body(body: Dict[str, Any]) -> Dict[str, Any]:
    return {"body": json.dumps(body)}


def test_pre_parse_modifies_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "LAMINA_PRE_PARSE_CALLBACK", "tests.custom_hooks:pre_parse_modify"
    )

    @lamina()
    def handler(request: Request):
        # request.data is the raw string body when no schema_in is provided
        return json.loads(request.data)

    response = handler(_event_with_body({"foo": "bar"}), None)
    body = json.loads(response["body"])

    assert body == {"foo": "modified"}
    assert response["statusCode"] == 200


def test_pre_execute_adjusts_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "LAMINA_PRE_EXECUTE_CALLBACK", "tests.custom_hooks:pre_execute_adjust"
    )

    @lamina()
    def handler(request: Request):
        return json.loads(request.data)

    response = handler(_event_with_body({"foo": "bar"}), None)
    body = json.loads(response["body"])

    assert body == {"foo": "pre"}


def test_pos_execute_can_return_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "LAMINA_POS_EXECUTE_CALLBACK", "tests.custom_hooks:pos_execute_tuple"
    )

    @lamina()
    def handler(request: Request):
        return {"ok": True}

    response = handler(_event_with_body({}), None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 201
    assert response["headers"]["X-Pos"] == "1"
    assert body["ok"] is True and body["pos"] is True


def test_pre_response_mutates_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "LAMINA_PRE_RESPONSE_CALLBACK", "tests.custom_hooks:pre_response_add_key"
    )

    @lamina()
    def handler(request: Request):
        return {"hello": "world"}

    response = handler(_event_with_body({}), None)
    body = json.loads(response["body"])

    assert body == {"hello": "world", "pre_response": True}
    assert response["headers"]["Content-Type"] == "application/json; charset=utf-8"


def test_invalid_hook_shows_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAMINA_PRE_PARSE_CALLBACK", "does.not.exist:func")

    @lamina()
    def handler(request: Request):
        return json.loads(request.data)

    response = handler(_event_with_body({"x": 1}), None)
    body = json.loads(response["body"])

    assert body == {
        "error_message": "Could not import 'does.not.exist:func' for setting "
        "'LAMINA_PRE_PARSE_CALLBACK'"
    }
    assert response["statusCode"] == 500
