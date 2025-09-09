from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union


# Helper hooks used by unit tests. They are referenced via environment variables
# so that lamina.config.get_hooks() imports them by string paths.


def pre_parse_modify(
    event: Union[Dict[str, Any], bytes, str],
    context: Optional[Dict[str, Any]],
) -> Union[Dict[str, Any], bytes, str]:
    """Modify the incoming event body if it is a dict with a body key.

    This simulates a pre-parse normalization step.
    """

    if isinstance(event, dict) and "body" in event:
        event = {**event, "body": '{"foo": "modified"}'}
    return event


def pre_execute_adjust(
    request: Any,
    event: Union[Dict[str, Any], bytes, str],
    context: Optional[Dict[str, Any]],
) -> Any:
    """Adjust the Request object before handler execution."""

    # Overwrite the request data to a known value used by tests
    request.data = '{"foo": "pre"}'
    return request


def pos_execute_tuple(response: Any, request: Any) -> Any:
    """Transform the handler response into a tuple (payload, status, headers)."""

    payload = response
    if isinstance(response, dict):
        payload = {**response, "pos": True}
    return payload, 201, {"X-Pos": "1"}


def pre_response_add_key(body: Any) -> Any:
    """Mutate the final body string by adding a JSON key if possible."""

    if isinstance(body, str):
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                data["pre_response"] = True
                return json.dumps(data)
        except Exception:
            return body
    return body
