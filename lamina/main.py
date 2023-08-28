import asyncio
import functools
import inspect
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, Union

from loguru import logger
from pydantic import BaseModel, ValidationError

from lamina.helpers import DecimalEncoder

CHARSET_UTF = "application/json; charset=utf-8"


@dataclass
class Request:
    data: Union[BaseModel, str]
    event: Union[Dict[str, Any], bytes, str]
    context: Optional[Dict[str, Any]]


def lamina(
    schema_in: Optional[Type[BaseModel]] = None,
    schema_out: Optional[Type[BaseModel]] = None,
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
                    data = event["body"]
                else:
                    request_body = json.loads(event["body"])
                    data = schema_in(**request_body)
                status_code = 200
                request = Request(
                    data=data,
                    event=event,
                    context=context,
                )

                # check if function is a coroutine
                if inspect.iscoroutinefunction(f):
                    response = asyncio.run(f(request))
                else:
                    response = f(request)

                if isinstance(response, tuple):
                    response, status_code = response

                if schema_out is None:
                    body = json.dumps(response, cls=DecimalEncoder)
                else:
                    body = schema_out(**response).model_dump_json(by_alias=True)

                return {
                    "statusCode": status_code,
                    "headers": {
                        "Content-Type": CHARSET_UTF,
                    },
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
                    "content-type": CHARSET_UTF,
                }
            except (ValueError, TypeError) as e:
                message = f"Error when attempt to read received body: {event['body']}."
                logger.error(str(e))
                return {
                    "statusCode": 400,
                    "body": json.dumps(message),
                    "headers": {
                        "Content-Type": CHARSET_UTF,
                    },
                }

        return wrapper

    return decorator
