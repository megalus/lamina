<h1 align="center">Welcome to Lamina</h1>

<p align="center">
<a href="https://pypi.org/project/py-lamina/" target="_blank">
<img alt="PyPI" src="https://img.shields.io/pypi/v/py-lamina"/></a>
<a href="https://www.python.org" target="_blank">
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/py-lamina"/>
</a>
<a href="https://github.com/megalus/lamina/blob/main/LICENSE" target="_blank">
<img alt="License: MIT" src="https://img.shields.io/github/license/megalus/lamina"/>
</a>
<a href="https://github.com/megalus/lamina/actions/workflows/tests.yml" target="_blank">
<img alt="Build Status" src="https://img.shields.io/github/actions/workflow/status/megalus/lamina/tests.yml?branch=main"/>
</a>
</p>

## Overview

Lamina (from Portuguese "lâmina", meaning "layer" or "blade") is a lightweight decorator library for AWS Lambda functions. It adds a powerful layer to your Lambda handlers, simplifying development by:

- Integrating both synchronous and asynchronous code in a single function
- Using Pydantic models for robust input and output data validation
- Handling errors gracefully with appropriate HTTP status codes
- Formatting responses according to AWS API Gateway expectations
- Supporting different content types (JSON, HTML, plain text)
- Providing convenient access to the original event and context objects

## Why use Lamina?

AWS Lambda functions often require repetitive boilerplate code for input validation, error handling, and response formatting. Lamina eliminates this boilerplate, allowing you to focus on your business logic while it handles:

- Input validation using Pydantic models
- Error handling with appropriate HTTP status codes
- Response formatting with content type control
- Support for both synchronous and asynchronous functions
- Custom headers support
- AWS Step Functions integration

## Installation

```shell
$ pip install py-lamina
```

Lamina requires Python 3.11 or later and has dependencies on:
- pydantic - For data validation
- asgiref - For async/sync conversion utilities
- loguru - For logging

## Usage

### Basic Example

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
from typing import Any, Dict
from lamina import lamina, Request

@lamina(schema_in=ExampleInput, schema_out=ExampleOutput)
def handler(request: Request) -> Dict[str, Any]:
    response = {"message": f"Hello {request.data.name}, you are {request.data.age} years old!"}
    return response
```

#### Working with query parameters

You can also define Pydantic models for query parameters:

```python
# schemas.py
from pydantic import BaseModel
from typing import Any, Dict, Optional
from lamina import lamina, Request

class ExampleQueryParams(BaseModel):
    verbose: Optional[bool] = False

@lamina(params_in=ExampleQueryParams, schema_in=ExampleInput, schema_out=ExampleOutput)
def handler(request: Request) -> Dict[str, Any]:
    if request.query.verbose:
        response = {"message": f"Hello {request.data.name}, you are {request.data.age} years old!."}
    else:
        response = {"message": f"Hello World!"}
    return response
```


### Asynchronous Handlers

Lamina seamlessly supports both synchronous and asynchronous handlers:

```python
# main.py
import asyncio
from typing import Any, Dict
from lamina import lamina, Request

@lamina(schema_in=ExampleInput, schema_out=ExampleOutput)
async def handler(request: Request) -> Dict[str, Any]:
    # Perform async operations
    await asyncio.sleep(1)
    response = {"message": f"Hello {request.data.name}, you are {request.data.age} years old!"}
    return response
```

### Customizing Responses

#### Status Codes

The default status code is 200. You can customize it by returning a tuple:

```python
from typing import Any, Dict
from lamina import lamina, Request

@lamina(schema_in=ExampleInput, schema_out=ExampleOutput)
def handler(request: Request):
    response = {"message": f"Hello {request.data.name}, you are {request.data.age} years old!"}
    return response, 201  # Created status code
```

#### Content Types

Lamina autodiscovers the content-type based on the return type:

```python
from lamina import lamina, Request

@lamina(schema_in=ExampleInput)
def handler(request: Request):
    html = f"""
        <html>
            <head><title>User Profile</title></head>
            <body>
                <h1>Hello {request.data.name}!</h1>
                <p>You are {request.data.age} years old.</p>
            </body>
        </html>
    """
    return html
```

You can explicitly set the content type using the `content_type` parameter:

```python
@lamina(schema_in=ExampleInput, content_type="text/plain; charset=utf-8")
def handler(request: Request):
    return f"Hello {request.data.name}, you are {request.data.age} years old!"
```

#### Custom Headers

You can add custom headers by returning them as the third element in the response tuple:

```python
@lamina(schema_in=ExampleInput)
def handler(request: Request):
    response = {"message": f"Hello {request.data.name}!"}
    return response, 200, {
        "Cache-Control": "max-age=3600",
        "X-Custom-Header": "custom-value"
    }
```

## Hooks

Lamina provides four extensibility points executed around your handler.

Configuration (pyproject.toml):

```toml
[tool.lamina]
pre_parse_callback = "lamina.hooks.pre_parse"
pre_execute_callback = "lamina.hooks.pre_execute"
pos_execute_callback = "lamina.hooks.pos_execute"
pre_response_callback = "lamina.hooks.pre_response"
```

Environment variables override these values at runtime:
- LAMINA_PRE_PARSE_CALLBACK
- LAMINA_PRE_EXECUTE_CALLBACK
- LAMINA_POS_EXECUTE_CALLBACK
- LAMINA_PRE_RESPONSE_CALLBACK

Hook signatures and responsibilities:
- pre_parse(event, context) -> event
- pre_execute(request, event, context) -> request
- pos_execute(response, request) -> response
- pre_response(body, request) -> body

### The Request Object

The `Request` object provides access to:

- `data`: The validated input data (as a Pydantic model if schema_in is provided)
- `event`: The original AWS Lambda event
- `context`: The original AWS Lambda context
- `query`: Query parameters from the event (as a Pydantic model if params_in is provided)
- `headers`: Headers from the AWS Lambda event

### Using Without Schemas

You can use Lamina without schemas for more flexibility:

```python
import json
from lamina import lamina, Request

@lamina()
def handler(request: Request):
    # Parse the body manually
    body = json.loads(request.event["body"])
    name = body.get("name", "Guest")
    age = body.get("age", "unknown")

    return {
        "message": f"Hello {name}, you are {age} years old!"
    }
```

> **Note**: Without a schema_in, the `request.data` attribute contains the raw body string from the event. You'll need to parse and validate it manually.

### AWS Step Functions Integration

Lamina supports AWS Step Functions with the `step_functions` parameter:

```python
@lamina(schema_in=ExampleInput, schema_out=ExampleOutput, step_functions=True)
def handler(request: Request):
    # For Step Functions, the input is directly available as the event
    # No need to parse from event["body"]
    return {
        "message": f"Step function processed for {request.data.name}"
    }
```

### Error Handling

Lamina automatically handles common errors:

- **Validation Errors**: Returns 400 Bad Request with detailed validation messages
- **Type Errors**: Returns 400 Bad Request when input cannot be parsed
- **Serialization Errors**: Returns 500 Internal Server Error when output cannot be serialized
- **Unhandled Exceptions**: Returns 500 Internal Server Error with the error message

All errors are logged using the loguru library for easier debugging.

## Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository** and clone it locally
2. **Create a new branch** for your feature or bugfix
3. **Make your changes** and add tests if applicable
4. **Run the tests** to ensure they pass: `poetry run pytest`
5. **Submit a pull request** with a clear description of your changes

Please make sure your code follows the project's style guidelines by running:
```shell
poetry run pre-commit run --all
```

### Development Setup

1. Clone the repository
2. Install dependencies with Poetry:
   ```shell
   poetry install
   ```
3. Install pre-commit hooks:
   ```shell
   poetry run pre-commit install
   ```

## License

This project is licensed under the terms of the MIT license.


## OpenAPI (Swagger) 3.1 Generation

Lamina can generate an OpenAPI 3.1 document by inspecting your decorated handlers and the metadata you place inside your Pydantic models using `json_schema_extra`.

### How it works:
- You can  pass the path directly in the decorator: `@lamina(path="/items" ...)`. If `path` is omitted, Lamina will derive it from the function name in kebab-case (e.g., `foo_bar` -> `/foo-bar`).
- Custom responses can be declared in the decorator via `responses={404: {"schema": ErrorOut}}`.
- All views automatically include `400` and `500` responses that reflect Lamina's built-in error handling.
- Paths in the generated Swagger UI are listed in alphabetical order by path.
- Authentication settings can be provided to `get_openapi_spec`. If not provided, the default is API Key in header `Authorization`.
- You can pass accepted HTTP methods via the decorator: `@lamina(methods=["get", "post"])`. If omitted, the default is `POST` (API Gateway typical default). You can still indicate a method in `json_schema_extra` for backward compatibility.
- Put operation metadata like `summary`, `description`, `tags`, and `operationId` in `json_schema_extra` of your `schema_in`, `schema_out`, or `params_in` models. If keys appear in multiple models, later ones override earlier ones.
- Provide the `path` via the decorator (recommended). If not set, it falls back to model extras and finally to the function name as explained above.
- Operation summary/description are derived from the handler docstring when present: the first line is used as summary and the following free-text (until Args/Returns/etc.) as description. If no docstring is present, the generator falls back to json_schema_extra values; if neither exists, the summary becomes the function name in title case (e.g., foo_bar -> Foo Bar) and the description is empty.
- You can exclude a handler from the generated spec by setting `add_to_spec=False` in the decorator (useful for HTML endpoints or internal views).
- Handlers without schemas (e.g., `@lamina()` with no `schema_in`/`schema_out`) are ignored by the spec generator unless sufficient metadata is available via models.
- Call `get_openapi_spec(...)` to receive a Python dict ready to be dumped as JSON.

Example:

```python
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict
from lamina import lamina, Request, get_openapi_spec


class CreateItemIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "method": "post",
            "summary": "Create an item",
            "tags": ["items"],
        }
    )
    name: str


class CreateItemOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"description": "Created item"})
    id: int
    name: str


@lamina(path="/items", schema_in=CreateItemIn, schema_out=CreateItemOut)
def create_item(request: Request) -> Dict[str, Any]:
    return {"id": 1, "name": request.data.name}


# Later (e.g., in a CLI or during startup)
spec = get_openapi_spec(title="My API", version="1.0.0", host="api.example.com", base_path="/v1")

# Dump as JSON
import json
print(json.dumps(spec, indent=2))
```

Custom responses and authentication:

```python
from pydantic import BaseModel

class ErrorOut(BaseModel):
    detail: str

@lamina(path="/items/{id}", schema_in=CreateItemIn, responses={404: {"schema": ErrorOut}})
def get_item(request: Request) -> Dict[str, Any]:
    ...

# Default auth is API Key via Authorization header
spec_default_auth = get_openapi_spec(title="My API", version="1.0.0")

# Custom bearer auth
spec_bearer = get_openapi_spec(
    title="My API",
    version="1.0.0",
    security_schemes={"BearerAuth": {"type": "http", "scheme": "bearer"}},
    security=[{"BearerAuth": []}],
)
```

The resulting document follows the OpenAPI 3.1 structure with:
- `paths` determined by the decorator or model extras and sorted alphabetically.
- `components.schemas` containing the Pydantic-generated JSON Schemas for your models.
- Query parameters auto-generated from `params_in` models (basic types).
- `400` and `500` responses automatically included for each operation. Add more with the `responses` argument on the decorator.

Notes:
- You can also pass a list of explicit server URLs using `servers=["https://api.example.com/v1"]` instead of `host`/`base_path`.
- If `path` is not provided in the decorator, it falls back to model extras and then to the kebab-case function name.

### Validate your OpenAPI document

You can validate the generated OpenAPI 3.1 spec using the openapi-schema-validator library.

Example:

```python
from pydantic import BaseModel, ConfigDict
from lamina import lamina, Request, get_openapi_spec
from openapi_schema_validator import validate as oas_validate, OAS31Validator

class In(BaseModel):
    model_config = ConfigDict(json_schema_extra={"method": "post"})
    name: str

class Out(BaseModel):
    ok: bool

@lamina(path="/ping", schema_in=In, schema_out=Out)
def ping(request: Request):
    return {"ok": True}

spec = get_openapi_spec(title="My API", version="1.0.0")

# Raises an exception if invalid
oas_validate(spec, cls=OAS31Validator)
```

This is the same approach used in our unit tests to ensure the generated spec conforms to the official OpenAPI 3.1 schema.
