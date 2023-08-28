# Welcome to Lamina

<p align="center">
<a href="https://pypi.org/project/py-lamina/" target="_blank">
<img alt="PyPI" src="https://img.shields.io/pypi/v/py-lamina"/></a>
<a href="https://www.python.org" target="_blank">
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/py-lamina"/>
</a>
</p>

This library adds a new layer ("lâmina") to AWS lambda functions, integrating synchronous and asynchronous code in a
single function, which use Pydantic models to validate input and output data.

---

### Install

```shell
$ pip install py-lamina
```

This library is compatible with Python 3.9, 3.10 and 3.11.

---

### Usage

Create the models for Input and Output data:

```python
# schemas.py

from pydantic import BaseModel

class ExampleInput(BaseModel):
    name: str
    age: int

class ExampleOutput(BaseModel):
    message: str
```

Create your AWS Lambda handler:

```python
# main.py
from typing import Any, Dict, Tuple, Union
from lamina import lamina, Request
from .schemas import ExampleInput, ExampleOutput

@lamina(schema=ExampleInput, schema_out=ExampleOutput)
def handler(request: Request) -> Dict[str, Any]:
    response = {"message": f"Hello {request.data.name}, you are {request.data.age} years old!"}
    return response
```

You can also use an async handler:

```python
# main.py
import asyncio

@lamina(schema=ExampleInput, schema_out=ExampleOutput)
async def handler(request: Request) -> Dict[str, Any]:
    await asyncio.sleep(1)
    response = {"message": f"Hello {request.data.name}, you are {request.data.age} years old!"}
    return response
```

### The Response Status Code
Default value is 200. You can change it by returning a tuple with the response and the status code:

```python
@lamina(schema=ExampleInput, schema_out=ExampleOutput)
def handler(request: Request) -> Tuple[Dict[str, Any], int]:
    response = {"message": f"Hello {request.data.name}, you are {request.data.age} years old!"}
    return response, 201
```

### The Request object

The `Request` object has the following attributes:
* `data`: The input data, already validated by the schema.
* `event`: The original event received by the lambda function.
* `context`: The original context received by the lambda function.

You can use lamina without one or both schemas, if you like:

```python
# main.py
import json
from typing import Any, Dict

from lamina import lamina, Request


@lamina()
def handler(request: Request) -> Dict[str, Any]:
    body = request.event["body"]
    data = json.loads(body)
    response = {"message": f"Hello {data.name}, you are {data.age} years old!"}
    return response
```

Please note, if you do not define a SchemaIn, the `data` attribute will contain the **original** body from event. You
need to validate it yourself and convert it to a dict, bytes, etc... you need before using the data received.

---

## License

This project is licensed under the terms of the MIT license.
