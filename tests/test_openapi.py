from typing import Any, Dict

import pytest
from openapi_spec_validator import validate
from pydantic import BaseModel, ConfigDict, Field

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
    assert "application/json" in content

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
