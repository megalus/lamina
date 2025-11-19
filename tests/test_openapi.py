import datetime
import os
from textwrap import dedent
from typing import Any, Dict

import pytest
from openapi_spec_validator import validate
from pydantic import BaseModel, ConfigDict, Field, RootModel

import lamina.main as lamina_main
from lamina import Request, get_openapi_spec, lamina


@pytest.fixture(scope="function", autouse=True)
def clear_registry():
    yield
    lamina_main.LAMINA_REGISTRY.clear()


def test_get_openapi_minimal():
    # Arrange
    class ItemIn(BaseModel):
        model_config = ConfigDict(
            json_schema_extra={
                "method": "post",
                "summary": "Create an item",
                "tags": ["items"],
            }
        )
        name: str

    class ItemOut(BaseModel):
        model_config = ConfigDict(json_schema_extra={"description": "Created item"})
        id: int
        name: str

    @lamina(path="/items", schema_in=ItemIn, schema_out=ItemOut)
    def handler(request: Request):
        return {"id": 1, "name": "foo"}

    # Act
    spec = get_openapi_spec(
        title="Test API", version="1.0.0", host="api.example.com", base_path="/v1"
    )

    # Assert
    # Top-level assertions
    assert spec["openapi"] == "3.1.0"
    assert spec["info"]["title"] == "Test API"
    assert spec["info"]["version"] == "1.0.0"
    assert spec["servers"][0]["url"].endswith("/v1")

    # Paths and operation
    assert "/items" in spec["paths"]
    post_op = spec["paths"]["/items"]["post"]
    assert post_op["summary"] == "Create an item"
    assert post_op["tags"] == ["items"]

    # Request body is present
    assert "requestBody" in post_op
    content = post_op["requestBody"]["content"]
    assert content == {
        "application/json; charset=utf-8": {
            "schema": {"$ref": "#/components/schemas/ItemIn"}
        }
    }

    # Response
    assert "200" in post_op["responses"]

    # Components contain the two models
    schemas = spec["components"]["schemas"]
    assert "ItemIn" in schemas
    assert "ItemOut" in schemas


def test_field_level_attributes_in_schema():
    # Arrange
    class FieldModel(BaseModel):
        name: str = Field(
            ...,
            title="Name",
            description="The item name",
            json_schema_extra={"x-extra": True},
        )
        age: int = Field(..., title="Age", description="The item age", examples=[10])

    # Need a method for inclusion in spec
    class DummyIn(BaseModel):
        model_config = ConfigDict(json_schema_extra={"method": "post"})
        data: Dict[str, Any]

    @lamina(schema_in=DummyIn, schema_out=FieldModel)
    def produce(request: Request):
        return {"name": "a", "age": 1}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    schemas = spec["components"]["schemas"]
    props = schemas["FieldModel"]["properties"]

    # Assert
    assert "FieldModel" in schemas
    assert props["name"]["title"] == "Name"
    assert props["name"]["description"] == "The item name"
    assert props["age"]["title"] == "Age"
    assert props["age"]["description"] == "The item age"


@pytest.mark.parametrize(
    "use_module, expected",
    [
        ("package", "/tests"),
        ("module", "/test-openapi"),
        ("function", "/foo-bar"),
    ],
)
def test_decorator_path_defaults_to_kebabcase(use_module, expected, monkeypatch):
    # Arrange
    monkeypatch.setenv("LAMINA_USE_OBJECT_NAME", use_module)

    class Meta(BaseModel):
        model_config = ConfigDict(json_schema_extra={"method": "get"})
        x: int

    @lamina(schema_in=Meta)
    def foo_bar(request: Request):
        return {"x": 1}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    paths = list(spec["paths"].keys())

    # Assert
    assert expected in paths


def test_decorator_path_overrides_model_extra():
    # Arrange
    class Meta(BaseModel):
        model_config = ConfigDict(json_schema_extra={"method": "get", "path": "/wrong"})
        x: int

    @lamina(path="/right", schema_in=Meta)
    def some_handler(request: Request):
        return {"x": 1}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")

    # Assert
    assert "/right" in spec["paths"]
    assert "/wrong" not in spec["paths"]


def test_custom_responses_and_default_errors():
    # Arrange
    class ErrorOut(BaseModel):
        detail: str

    class Meta(BaseModel):
        model_config = ConfigDict(json_schema_extra={"method": "get"})
        id: int

    @lamina(path="/items/{id}", schema_in=Meta, responses={404: {"schema": ErrorOut}})
    def get_item(request: Request):
        return {"detail": "not used here"}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    op = spec["paths"]["/items/{id}"]["get"]
    res = op["responses"]

    # Assert
    assert "404" in res
    assert "400" in res
    assert "500" in res
    # Ensure the ErrorOut schema is present
    assert "ErrorOut" in spec["components"]["schemas"]


def test_paths_ordering_alphabetical():
    # Arrange
    class Meta(BaseModel):
        model_config = ConfigDict(json_schema_extra={"method": "get"})
        x: int

    @lamina(path="/b", schema_in=Meta)
    def handler_b(request: Request):
        return {"x": 1}

    @lamina(path="/a", schema_in=Meta)
    def handler_a(request: Request):
        return {"x": 2}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    paths = list(spec["paths"].keys())

    # Assert
    assert paths == sorted(paths)


def test_authentication_default_and_custom():
    # Arrange
    class Meta(BaseModel):
        x: int

    @lamina(schema_in=Meta, methods=["GET"])
    def any_handler(request: Request):
        return {"x": 1}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    comps = spec["components"]
    custom = get_openapi_spec(
        title="Test",
        version="1.0.0",
        security_schemes={"BearerAuth": {"type": "http", "scheme": "bearer"}},
        security=[{"BearerAuth": []}],
    )

    # Assert
    assert "securitySchemes" in comps
    assert "BearerAuth" in custom["components"]["securitySchemes"]
    assert custom["security"] == [{"BearerAuth": []}]


def test_openapi_spec_validates_with_oas31():
    # Arrange
    class PingIn(BaseModel):
        model_config = ConfigDict(json_schema_extra={"method": "post"})
        name: str = Field(
            ...,
            examples=["Alice"],
            title="Name",
            description="Your name",
            json_schema_extra={"example": "Alice"},
        )

    class PingOut(BaseModel):
        ok: bool = Field(
            ..., title="OK", description="Indicates if the ping was successful"
        )

    @lamina(path="/ping", schema_in=PingIn, schema_out=PingOut)
    def ping(request: Request):
        return {"ok": True}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")

    # Assert
    validate(dict(spec))


def test_minimal_lamina_handler_is_ignored_and_spec_is_valid():
    # Arrange
    @lamina()
    def plain(request: Request):
        return "ok"

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")

    # Assert
    assert spec["paths"] == {}
    validate(dict(spec))


def test_add_to_spec_false_excludes_view_from_spec():
    # Arrange
    class Meta(BaseModel):
        model_config = ConfigDict(json_schema_extra={"method": "get"})
        x: int

    @lamina(schema_in=Meta, add_to_spec=False)
    def hidden(request: Request):
        return {"x": 1}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")

    # Assert
    assert spec["paths"] == {}
    validate(dict(spec))


def test_methods_decorator_and_default_post():
    # Arrange
    class InModel(BaseModel):
        model_config = ConfigDict(json_schema_extra={})
        x: int

    class OutModel(BaseModel):
        ok: bool

    @lamina(
        path="/multi", schema_in=InModel, schema_out=OutModel, methods=["GET", "POST"]
    )
    def multi(request: Request):
        return {"ok": True}

    @lamina(path="/default", schema_in=InModel, schema_out=OutModel)
    def default(request: Request):
        return {"ok": True}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")

    # Assert
    assert "get" in spec["paths"]["/multi"]
    assert "post" in spec["paths"]["/multi"]
    assert list(spec["paths"]["/default"].keys()) == ["post"]


def test_docstring_summary_and_description_and_defaults():
    # Arrange
    class PingIn(BaseModel):
        name: str

    class PingOut(BaseModel):
        ok: bool

    @lamina(
        path="/doc", schema_in=PingIn, schema_out=PingOut, methods=["post"]
    )  # ensure inclusion
    def do_ping(request: Request):
        """Ping endpoint

        This endpoint pings the *server* and returns a simple OK payload.
        It is used for health checks.

        Args:
            request: The lamina Request object
        Returns:
            A PingOut model
        """
        return {"ok": True}

    @lamina(path="/no-doc", schema_in=PingIn, schema_out=PingOut)
    def foo_bar(request: Request):
        return {"ok": True}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    op = spec["paths"]["/doc"]["post"]
    op2 = spec["paths"]["/no-doc"]["post"]

    # Assert
    assert op["summary"] == "Ping endpoint"
    assert "health checks" in op["description"]
    assert "<em>" in op["description"]
    assert "Args:" not in op["description"]
    assert op2["summary"] == "No Doc"
    assert op2["description"] == ""


mod_time = os.path.getmtime(__file__)
last_updated = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")

expected_result = f"""<h3>Paragraphs and Text Formatting</h3>
<p>This is a <strong>bold</strong> statement.</p>
<p>This is an <em>italic</em> word.</p>
<p>This is a <code>code snippet</code>.</p>
<p>This is a <em><strong>bold-italic</strong></em></p>
<p>And this is <del>strikethrough</del> text.</p>
<p>Finally, this is a block of code:</p>
<pre><code class="language-python">def hello_world():
    print(&quot;Hello, World!&quot;)
</code></pre>
<h2>This is the lists</h2>
<h3>This is a bullet list:</h3>
<ul>
<li>Item 1</li>
<li>Item 2</li>
<li>Item 3</li>
</ul>
<h3>And this is a numbered list:</h3>
<ol>
<li>First</li>
<li>Second</li>
<li>Third</li>
<li>Fourth</li>
</ol>
<h3>Links</h3>
<p>Here is a <a href="https://example.com">link</a> to an example website.</p>
<h3>Tables</h3>
<table>
<thead>
<tr>
  <th>Header 1</th>
  <th>Header 2</th>
</tr>
</thead>
<tbody>
<tr>
  <td>Cell 1</td>
  <td>Cell 2</td>
</tr>
<tr>
  <td>Cell 3</td>
  <td>Cell 4</td>
</tr>
</tbody>
</table>
<h3>Mermaid Diagram</h3>
<pre><code class="language-mermaid">graph TD;
    A--&gt;B;
    A--&gt;C;
    B--&gt;D;
    C--&gt;D;
</code></pre>
<hr><p><em>Document Last Updated: {last_updated}</em></p>"""


def test_markdown_to_html_in_descriptions():
    # Arrange
    class InModel(BaseModel):
        x: int

    @lamina(path="/convert", schema_in=InModel)
    def markdown_handler(request: Request):
        """Test Markdown Conversion.

        ### Paragraphs and Text Formatting
        This is a **bold** statement.

        This is an _italic_ word.

        This is a `code snippet`.

        This is a _**bold-italic**_

        And this is ~~strikethrough~~ text.

        Finally, this is a block of code:
        ```python
        def hello_world():
            print("Hello, World!")
        ```

        ## This is the lists
        ### This is a bullet list:
        - Item 1
        - Item 2
        - Item 3

        ### And this is a numbered list:
        1. First
        2. Second
        3. Third
        4. Fourth

        ### Links
        Here is a [link](https://example.com) to an example website.

        ### Tables
        | Header 1 | Header 2 |
        |----------|----------|
        | Cell 1   | Cell 2   |
        | Cell 3   | Cell 4   |

        ### Mermaid Diagram
        ```mermaid
        graph TD;
            A-->B;
            A-->C;
            B-->D;
            C-->D;
        ```

        """
        return {"x": 1}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    desc = spec["paths"]["/convert"]["post"]["description"]

    # Assert
    assert dedent(desc) == dedent(expected_result)


def test_custom_content_types():
    """Check custom request and response content types are in the OpenAPI spec.

    In this test, expected results in POST /custom are:
    * Accepts: application/octet-stream
    * Returns: text/plain

    """

    # Arrange
    class InModel(RootModel[bytes]):
        pass

    class OutModel(RootModel[str]):
        pass

    @lamina(
        path="/custom",
        schema_in=InModel,
        schema_out=OutModel,
        accepts="application/octet-stream",
        produces="text/plain",
    )
    def custom_content_handler(request: Request):
        return "custom response"

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    op = spec["paths"]["/custom"]["post"]
    request_content = op["requestBody"]["content"]
    response_content = op["responses"]["200"]["content"]

    # Assert
    assert request_content == {
        "application/octet-stream": {
            "schema": {"$ref": "#/components/schemas/InModel"},
        }
    }
    assert response_content == {
        "text/plain": {"schema": {"$ref": "#/components/schemas/OutModel"}}
    }
