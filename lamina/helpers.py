import asyncio
import json
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Callable, Coroutine, Union

from asgiref.sync import SyncToAsync, sync_to_async


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, date):
            return o.isoformat()
        return super(DecimalEncoder, self).default(o)


def async_(func: Callable) -> Union[Coroutine, SyncToAsync, Callable]:
    """Returns a coroutine function."""
    return func if asyncio.iscoroutinefunction(func) else sync_to_async(func)


class Lamina(Enum):
    JSON = "application/json; charset=utf-8"
    TEXT = "text/plain; charset=utf-8"
    HTML = "text/html; charset=utf-8"
