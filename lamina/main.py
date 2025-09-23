import asyncio
import functools
import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type, TypedDict, Union

import magic
from loguru import logger
from pydantic import BaseModel, RootModel, ValidationError

from lamina import conf
from lamina.helpers import DecimalEncoder

# Global registry of lamina-decorated handlers (wrappers)
LAMINA_REGISTRY: list[Callable[..., Any]] = []


@dataclass
class Request:
    """Request object passed to decorated handlers.

    Attributes:
        data: Parsed body or model instance according to schema_in and flags.
        event: Original AWS Lambda event.
        context: Lambda context object.
        query: Optional parsed query parameters if params_in schema is provided.
    """

    data: Union[BaseModel, str]
    event: Union[Dict[str, Any], bytes, str]
    context: Optional[Dict[str, Any]]
    headers: Optional[Dict[str, Any]]
    query: Optional[BaseModel] = None


class ResponseDict(TypedDict):
    statusCode: int
    headers: Dict[str, str]
    body: str


def lamina(
    schema_in: Optional[Type[BaseModel] | Type[RootModel]] = None,
    schema_out: Optional[Type[BaseModel] | Type[RootModel]] = None,
    params_in: Optional[Type[BaseModel] | Type[RootModel]] = None,
    content_type: str | None = None,
    step_functions: bool = False,
    path: Optional[str] = None,
    responses: Optional[Dict[int, Dict[str, Any]]] = None,
    add_to_spec: bool = True,
    methods: Optional[list[str]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., ResponseDict]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., ResponseDict]:
        @functools.wraps(f)
        def wrapper(
            event: Dict[str, Any] | bytes | str,
            context: Optional[Dict[str, Any]],
            *args: Any,
            **kwargs: Any,
        ) -> ResponseDict:
            if f.__doc__:
                title = f.__doc__.split("\n")[0].strip()
            else:
                # event may not be a dict; guard get
                path = event.get("path") if isinstance(event, dict) else "unknown"
                title = f"{f.__name__} for path {path}"
            logger.info(f"******* {title.upper()} *******")
            logger.debug(event)

            magic_content_type = "application/json"

            try:
                # Run pre-parse hook (may adjust event)
                pre_parse_hook = conf.LAMINA_PRE_PARSE_CALLBACK
                if inspect.iscoroutinefunction(pre_parse_hook):
                    event = asyncio.run(pre_parse_hook(event, context))
                else:
                    event = pre_parse_hook(event, context)

                # Parse Headers
                headers = event.get("headers", {}) if isinstance(event, dict) else {}
                if headers is None:
                    headers = {}

                # Parse Params if schema provided
                query_info = None
                if params_in:
                    query_data = (
                        event.get("queryStringParameters", {})
                        if isinstance(event, dict)
                        else {}
                    )
                    query_info = params_in(**query_data)

                # Parse input (after possible pre-parse modification)
                if schema_in is None:
                    data = (
                        event["body"]
                        if (isinstance(event, dict) and not step_functions)
                        else event
                    )
                else:
                    request_body = (
                        json.loads(event["body"])
                        if (isinstance(event, dict) and not step_functions)
                        else event
                    )
                    data = schema_in(**request_body)

                # Build initial Request and run pre-execute hook
                request = Request(
                    data=data,
                    event=event,
                    context=context,
                    query=query_info,
                    headers=headers,
                )
                pre_execute_hook = conf.LAMINA_PRE_EXECUTE_CALLBACK
                if inspect.iscoroutinefunction(pre_execute_hook):
                    request = asyncio.run(pre_execute_hook(request, event, context))
                else:
                    request = pre_execute_hook(request, event, context)

                status_code = 200

                headers: Dict[str, str] = {}

                # check if function is a coroutine
                if inspect.iscoroutinefunction(f):
                    response: Any = asyncio.run(f(request))
                else:
                    response = f(request)

                # Execute post-execution hook on raw response (before schema_out)
                pos_execute_hook = conf.LAMINA_POS_EXECUTE_CALLBACK
                if inspect.iscoroutinefunction(pos_execute_hook):
                    response = asyncio.run(pos_execute_hook(response, request))
                else:
                    response = pos_execute_hook(response, request)

                if isinstance(response, tuple):
                    status_code = response[1]
                    if len(response) == 3:
                        headers = response[2]
                    response = response[0]

                try:
                    body: str | Any = response
                    if body:
                        if schema_out:
                            if issubclass(schema_out, RootModel):
                                root = schema_out(response).root
                                if root is not None:
                                    body = (
                                        schema_out(response).model_dump_json(
                                            by_alias=True
                                        )
                                        if not isinstance(root, str)
                                        else root
                                    )
                            else:
                                body = schema_out(**response).model_dump_json(
                                    by_alias=True
                                )
                        body = (
                            json.dumps(body, cls=DecimalEncoder)
                            if not isinstance(body, str)
                            else body
                        )
                    magic_content_type = (
                        magic.from_buffer(body, mime=True) if body else "text/html"
                    )
                except Exception as e:
                    # This is an Internal Server Error
                    logger.error(f"Error when attempt to serialize response: {e}")
                    status_code = 500
                    body = json.dumps(
                        [
                            {
                                "field": (
                                    schema_out.__name__ if schema_out else "DumpJson"
                                ),
                                "message": str(e),
                            }
                        ],
                        cls=DecimalEncoder,
                    )

                full_headers: Dict[str, str] = {
                    "Content-Type": content_type
                    or f"{magic_content_type}; charset=utf-8",
                }
                if headers:
                    full_headers.update(headers)

                # Run pre-response hook just before returning
                pre_response_hook = conf.LAMINA_PRE_RESPONSE_CALLBACK
                if inspect.iscoroutinefunction(pre_response_hook):
                    body = asyncio.run(pre_response_hook(body))  # type: ignore[misc]
                else:
                    body = pre_response_hook(body)

                return {
                    "statusCode": status_code,
                    "headers": full_headers,
                    "body": body,  # type: ignore[return-value]
                }
            except ValidationError as e:
                messages = [
                    {
                        "field": (
                            error["loc"][0] if error.get("loc") else "ModelValidation"
                        ),
                        "message": error["msg"],
                    }
                    for error in e.errors()
                ]
                logger.error(messages)
                body = json.dumps(messages)
                return {
                    "statusCode": 400,
                    "body": body,
                    "headers": {
                        "Content-Type": "application/json; charset=utf-8",
                    },
                }
            except (ValueError, TypeError) as e:
                message = f"Error when attempt to read received event: {event}."
                logger.error(str(e))
                body = json.dumps(message)
                return {
                    "statusCode": 400,
                    "body": body,
                    "headers": {
                        "Content-Type": "application/json; charset=utf-8",
                    },
                }
            except Exception as e:
                logger.exception(e)
                body = json.dumps({"error_message": str(e)})
                return {
                    "statusCode": 500,
                    "body": body,
                    "headers": {
                        "Content-Type": "application/json; charset=utf-8",
                    },
                }

        wrapper.schema_in = schema_in
        wrapper.schema_out = schema_out
        wrapper.content_type = content_type
        wrapper.params_in = params_in

        # Resolve path (decorator argument > default from function name)
        resolved_path = path
        if not resolved_path:
            # Convert function name snake_case to kebab-case
            name_part = f.__name__.replace("_", "-").lower()
            resolved_path = f"/{name_part}"
        elif not resolved_path.startswith("/"):
            resolved_path = f"/{resolved_path}"
        wrapper.path = resolved_path  # type: ignore[attr-defined]

        # Custom additional responses (e.g., {404: {"schema": ErrorOut}})
        wrapper.responses = responses or {}  # type: ignore[attr-defined]

        # Accepted HTTP methods for the handler (used by OpenAPI generator)
        # Keep as provided (None means generator may fallback to extras or defaults)
        wrapper.methods = methods  # type: ignore[attr-defined]

        # Register wrapper for OpenAPI generation
        if add_to_spec:
            try:
                LAMINA_REGISTRY.append(wrapper)
            except Exception:
                # Fallback: do not break if registry fails for some reason
                logger.debug("Unable to register lamina wrapper in registry.")

        return wrapper

    return decorator
