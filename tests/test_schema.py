import json
from typing import Dict

import pytest
from pydantic import BaseModel, RootModel

from lamina import Request, lamina


def test_both_schemas():
    # Arrange

    class SchemaIn(BaseModel):
        foo: str

    class SchemaOut(BaseModel):
        result: Dict[str, str]

    @lamina(schema_in=SchemaIn, schema_out=SchemaOut)
    def handler(request: Request):
        return {"result": request.data.model_dump()}

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)

    # Assert
    assert response == {
        "body": '{"result":{"foo":"bar"}}',
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "statusCode": 200,
    }


@pytest.mark.parametrize(
    "body, content_type",
    [
        ('{"foo": "bar"}', "text/plain; charset=utf-8"),
        (
            '{"foo": "<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?><book>'
            "<title>Python Guide</title><author>John Smith</author>"
            '<year>2023</year></book>"}',
            "text/xml; charset=utf-8",
        ),
        ('{"foo": "<html><h1>hello world</h1></html>"}', "text/html; charset=utf-8"),
    ],
)
def test_root_model(body, content_type):
    # Arrange

    class SchemaIn(BaseModel):
        foo: str

    class SchemaOut(RootModel):
        root: str

    @lamina(schema_in=SchemaIn, schema_out=SchemaOut)
    def handler(request: Request):
        return request.data.foo

    payload = json.loads(body)["foo"]

    # Act
    response = handler({"body": body}, None)

    # Assert
    assert response == {
        "body": payload,
        "headers": {"Content-Type": content_type},
        "statusCode": 200,
    }
