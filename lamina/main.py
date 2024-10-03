import asyncio
import functools
import inspect
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, Union

from loguru import logger
from pydantic import BaseModel, ValidationError

from lamina.helpers import DecimalEncoder, Lamina


@dataclass
class Request:
    data: Union[BaseModel, str]
    event: Union[Dict[str, Any], bytes, str]
    context: Optional[Dict[str, Any]]


def lamina(
    schema_in: Optional[Type[BaseModel]] = None,
    schema_out: Optional[Type[BaseModel]] = None,
    content_type: Lamina = Lamina.JSON,
        step_functions: bool = False,
):
    def decorator(f: callable):
        @functools.wraps(f)
        def wrapper(event, context, *args, **kwargs):
            if f.__doc__:
                title = f.__doc__.split("\n")[0].strip()
            else:
                title = f"{f.__name__} for path {event.get('path')}"
            logger.info(f"******* {title.upper()} *******")
            logger.debug(event)

            try:
                if schema_in is None:
                    data = event["body"] if not step_functions else event
                else:
                    request_body = json.loads(event["body"]) if not step_functions else json.load(event)
                    data = schema_in(**request_body)
                status_code = 200
                request = Request(
                    data=data,
                    event=event,
                    context=context,
                )

                headers = {}
                # check if function is a coroutine
                if inspect.iscoroutinefunction(f):
                    response = asyncio.run(f(request))
                else:
                    response = f(request)

                if isinstance(response, tuple):
                    status_code = response[1]
                    if len(response) == 3:
                        headers = response[2]
                    response = response[0]

                try:
                    body = response
                    if content_type == Lamina.JSON:
                        if schema_out is None:
                            body = json.dumps(response, cls=DecimalEncoder)
                        else:
                            body = schema_out(**response).model_dump_json(by_alias=True)
                except Exception as e:
                    # This is an Internal Server Error
                    logger.error(f"Error when attempt to serialize response: {e}")
                    status_code = 500
                    body = json.dumps(
                        [
                            {
                                "field": schema_out.__name__
                                if schema_out
                                else "DumpJson",
                                "message": str(e),
                            }
                        ],
                        cls=DecimalEncoder,
                    )

                full_headers = {
                    "Content-Type": content_type.value,
                }
                if headers:
                    full_headers.update(headers)

                return {
                    "statusCode": status_code,
                    "headers": full_headers,
                    "body": body,
                }
            except ValidationError as e:
                messages = [
                    {
                        "field": error["loc"][0]
                        if error.get("loc")
                        else "ModelValidation",
                        "message": error["msg"],
                    }
                    for error in e.errors()
                ]
                logger.error(messages)
                return {
                    "statusCode": 400,
                    "body": json.dumps(messages),
                    "content-type": content_type.value,
                }
            except (ValueError, TypeError) as e:
                message = f"Error when attempt to read received body: {event['body']}."
                logger.error(str(e))
                return {
                    "statusCode": 400,
                    "body": json.dumps(message),
                    "headers": {
                        "Content-Type": content_type.value,
                    },
                }
            except Exception as e:
                logger.exception(e)
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error_message": str(e)}),
                    "headers": {
                        "Content-Type": "application/json; charset=utf-8",
                    },
                }

        return wrapper

    return decorator
