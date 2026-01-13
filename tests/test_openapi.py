import datetime
import os
from decimal import Decimal
from enum import Enum
from textwrap import dedent
from typing import Any, Dict, Literal, Optional, Union

import pytest
from openapi_spec_validator import validate
from pydantic import UUID4, BaseModel, ConfigDict, Field, RootModel

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

markdown_expected_result = f"""<h3>Paragraphs and Text Formatting</h3>
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
<hr />
<h2>Request Body Fields</h2>
<table>
<thead>
<tr>
  <th>Field</th>
  <th>Type</th>
  <th>Required</th>
  <th>Default Value</th>
  <th>Description</th>
  <th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>x</strong></td>
  <td>integer</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>--</td>
  <td>--</td>
</tr>
</tbody>
</table>
<hr><p><em>Resource Last Updated: {last_updated}</em></p>"""


table_expected_result = f"""<p>This is the main description of the View.
Must be at the top.</p>
<hr />
<h2>This is the Query Parameters Title.</h2>
<p>Here is the description for the query parameters.</p>
<table>
<thead>
<tr>
  <th>Field</th>
  <th>Type</th>
  <th>Required</th>
  <th>Default Value</th>
  <th>Description</th>
  <th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>search</strong></td>
  <td>string</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>Search term for filtering items</td>
  <td>example</td>
</tr>
<tr>
  <td>limit</td>
  <td>integer</td>
  <td>No</td>
  <td>10</td>
  <td>Maximum number of items to return</td>
  <td>5</td>
</tr>
</tbody>
</table>
<hr />
<h2>This is the InModel Request Body Title.</h2>
<p>This is the InModel Request Body description.
Must be at the middle.</p>
<table>
<thead>
<tr>
  <th>Field</th>
  <th>Type</th>
  <th>Required</th>
  <th>Default Value</th>
  <th>Description</th>
  <th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>id</strong></td>
  <td>integer</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>The item ID</td>
  <td>1</td>
</tr>
<tr>
  <td><strong>name</strong></td>
  <td>string</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>The item name</td>
  <td>item</td>
</tr>
<tr>
  <td><strong>unitPrice</strong></td>
  <td>number</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>The price per unit</td>
  <td>9.99</td>
</tr>
<tr>
  <td><strong>unitType</strong></td>
  <td>enum</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>The type of unit</td>
  <td>--</td>
</tr>
<tr>
  <td>createdAt</td>
  <td>datetime</td>
  <td>No</td>
  <td>--</td>
  <td>The creation timestamp</td>
  <td>2024-01-01T12:00:00Z</td>
</tr>
<tr>
  <td>enabled</td>
  <td>boolean</td>
  <td>No</td>
  <td>True</td>
  <td>Whether the item is enabled</td>
  <td>--</td>
</tr>
<tr>
  <td>quantity</td>
  <td>integer</td>
  <td>No</td>
  <td>1</td>
  <td>The item quantity</td>
  <td>10</td>
</tr>
</tbody>
</table>
<hr />
<h2>This is the OutModel Response Body Title.</h2>
<p>Actual response is inside the 'result' field.</p>
<table>
<thead>
<tr>
  <th>Field</th>
  <th>Type</th>
  <th>Required</th>
  <th>Default Value</th>
  <th>Description</th>
  <th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>result</strong></td>
  <td>object</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>--</td>
  <td>--</td>
</tr>
</tbody>
</table>
<h3>This is the ResultModel Response Body Title.</h3>
<p>This is the ResultModel Response Body description.</p>
<table>
<thead>
<tr>
  <th>Field</th>
  <th>Type</th>
  <th>Required</th>
  <th>Default Value</th>
  <th>Description</th>
  <th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>id</strong></td>
  <td>integer</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>The result item ID</td>
  <td>1</td>
</tr>
</tbody>
</table>
<hr><p><em>Resource Last Updated: {last_updated}</em></p>"""

non_required_fields_expected_result = f"""<hr />
<h2>Request Body Fields</h2>
<table>
<thead>
<tr>
  <th>Field</th>
  <th>Type</th>
  <th>Required</th>
  <th>Default Value</th>
  <th>Description</th>
  <th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>requiredField</strong></td>
  <td>string</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>The field name</td>
  <td>--</td>
</tr>
<tr>
  <td>defaultValueField</td>
  <td>string</td>
  <td>No</td>
  <td>foo</td>
  <td>The field with a default value</td>
  <td>--</td>
</tr>
<tr>
  <td>nullableField</td>
  <td>string</td>
  <td>No</td>
  <td>--</td>
  <td>The nullable field</td>
  <td>--</td>
</tr>
<tr>
  <td>nullableWithDefaultField</td>
  <td>string</td>
  <td>No</td>
  <td>bar</td>
  <td>The nullable field with a default value</td>
  <td>--</td>
</tr>
</tbody>
</table>
<hr><p><em>Resource Last Updated: {last_updated}</em></p>"""


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
    assert dedent(desc) == dedent(markdown_expected_result)


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


def test_automatic_parameters():
    # Arrange
    class UnitType(Enum):
        PIECE = "piece"
        KG = "kg"
        LITER = "liter"

    class InModel(BaseModel):
        """This is the InModel Request Body Title.

        This is the InModel Request Body description.
        Must be at the middle.
        """

        id: int = Field(title="ID", examples=[1], description="The item ID")
        name: str = Field(title="Name", description="The item name", examples=["item"])
        quantity: int = Field(
            title="Quantity", default=1, description="The item quantity", examples=[10]
        )
        unit_price: Decimal = Field(
            alias="unitPrice",
            title="Unit Price",
            description="The price per unit",
            examples=["9.99"],
        )
        unit_type: UnitType = Field(
            alias="unitType",
            title="Unit Type",
            description="The type of unit",
            json_schema_extra={"enum": [e.value for e in UnitType]},
        )
        enabled: bool = Field(
            title="Enabled",
            default=True,
            description="Whether the item is enabled",
        )
        created_at: datetime.datetime = Field(
            alias="createdAt",
            title="Created At",
            default_factory=lambda: datetime.datetime.now(datetime.UTC),
            description="The creation timestamp",
            examples=["2024-01-01T12:00:00Z"],
        )

    class ResultModel(BaseModel):
        """This is the ResultModel Response Body Title.

        This is the ResultModel Response Body description.

        """

        id: int = Field(title="ID", description="The result item ID", examples=[1])

    class OutModel(BaseModel):
        """This is the OutModel Response Body Title.

        Actual response is inside the 'result' field.

        """

        result: ResultModel

    class QueryModel(BaseModel):
        """This is the Query Parameters Title.

        Here is the description for the query parameters.

        """

        search: str = Field(
            title="Search",
            description="Search term for filtering items",
            examples=["example"],
        )
        limit: int = Field(
            title="Limit",
            default=10,
            description="Maximum number of items to return",
            examples=[5],
        )

    @lamina(path="/items", params_in=QueryModel, schema_in=InModel, schema_out=OutModel)
    def create_item(request: Request):
        """Return an item by ID.

        This is the main description of the View.
        Must be at the top.

        """
        return {"id": request.data.id}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    html_desc = spec["paths"]["/items"]["post"]["description"]

    # Assert
    assert dedent(html_desc) == dedent(table_expected_result)


def test_required_fields_in_schema():
    # Arrange
    class InModel(BaseModel):
        required_field: str = Field(
            ...,
            alias="requiredField",
            title="Required Field",
            description="The field name",
        )
        default_value_field: str = Field(
            "foo",
            alias="defaultValueField",
            title="Default Value Field",
            description="The field with a default value",
        )
        nullable_field: str | None = Field(
            None,
            alias="nullableField",
            title="Nullable Field",
            description="The nullable field",
        )
        nullable_with_default_field: str | None = Field(
            "bar",
            alias="nullableWithDefaultField",
            title="Nullable With Default Field",
            description="The nullable field with a default value",
        )

    @lamina(path="/test", schema_in=InModel)
    def handler(request: Request):
        """Test required and non-required fields in schema."""
        return {"required_field": request.data.required_field}

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    html_desc = spec["paths"]["/test"]["post"]["description"]

    # Assert
    assert dedent(html_desc) == dedent(non_required_fields_expected_result)


optional_and_array_expected_result = f"""<hr />
<h2>Request Body Fields</h2>
<table>
<thead>
<tr>
  <th>Field</th>
  <th>Type</th>
  <th>Required</th>
  <th>Default Value</th>
  <th>Description</th>
  <th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>items</strong></td>
  <td>array[object]</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>List of sub-items</td>
  <td>--</td>
</tr>
<tr>
  <td><strong>numbers</strong></td>
  <td>array[integer, number]</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>A list of numbers</td>
  <td>--</td>
</tr>
<tr>
  <td>literal</td>
  <td>enum</td>
  <td>No</td>
  <td>LiteralValue</td>
  <td>A field with a literal value</td>
  <td>LiteralValue</td>
</tr>
<tr>
  <td>modelId</td>
  <td>uuid, string</td>
  <td>No</td>
  <td>--</td>
  <td>An optional model ID that can be UUID4 or string</td>
  <td>--</td>
</tr>
<tr>
  <td>optionalField</td>
  <td>boolean</td>
  <td>No</td>
  <td>False</td>
  <td>An optional field</td>
  <td>--</td>
</tr>
</tbody>
</table>
<h3>Sub Item</h3>
<table>
<thead>
<tr>
  <th>Field</th>
  <th>Type</th>
  <th>Required</th>
  <th>Default Value</th>
  <th>Description</th>
  <th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>id</strong></td>
  <td>integer</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>The sub-item ID</td>
  <td>1</td>
</tr>
<tr>
  <td><strong>name</strong></td>
  <td>string</td>
  <td><strong>Yes</strong></td>
  <td>--</td>
  <td>The sub-item name</td>
  <td>subitem</td>
</tr>
</tbody>
</table>
<hr><p><em>Resource Last Updated: {last_updated}</em></p>"""


def test_optional_and_array_fields_in_schema():
    # Arrange
    class SubItem(BaseModel):
        id: int = Field(..., title="ID", description="The sub-item ID", examples=[1])
        name: str = Field(
            ..., title="Name", description="The sub-item name", examples=["subitem"]
        )

    class InModel(BaseModel):
        items: list[SubItem] = Field(
            ...,
            title="Items",
            description="List of sub-items",
        )
        optional_field: Optional[bool] = Field(
            False,
            title="Optional Field",
            alias="optionalField",
            description="An optional field",
        )
        numbers: list[Union[int, float]] = Field(
            ...,
            title="Numbers",
            description="A list of numbers",
        )
        literal: Literal["LiteralValue"] = Field(
            "LiteralValue",
            title="Literal Field",
            description="A field with a literal value",
            examples=["LiteralValue"],
        )
        model_id: Optional[Union[UUID4, str]] = Field(
            None,
            title="Model ID",
            alias="modelId",
            description="An optional model ID that can be UUID4 or string",
        )

    @lamina(path="/optional-array", schema_in=InModel)
    def handler(request: Request):
        """Test optional and array fields in schema."""
        return {
            "items": request.data.items,
            "optional_field": request.data.optional_field,
        }

    # Act
    spec = get_openapi_spec(title="Test", version="1.0.0")
    html_desc = spec["paths"]["/optional-array"]["post"]["description"]

    # Assert
    assert dedent(html_desc) == dedent(optional_and_array_expected_result)
