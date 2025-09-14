import asyncio
import json

from pydantic import BaseModel

from lamina import Request, lamina


def test_sync_lambda():
    # Arrange
    @lamina()
    def handler(request: Request):
        return json.loads(request.data)

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)
    body = json.loads(response["body"])

    # Assert
    assert body == {"foo": "bar"}
    assert response == {
        "body": '{"foo": "bar"}',
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "statusCode": 200,
    }


def test_async_lambda():
    # Arrange
    @lamina()
    async def handler(request: Request):
        await asyncio.sleep(0.1)
        return json.loads(request.data)

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)

    # Assert
    assert response == {
        "body": '{"foo": "bar"}',
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "statusCode": 200,
    }


def test_get_schemas():
    # Arrange
    class SchemaIn(BaseModel):
        foo: str
        bar: int

    class SchemaOut(BaseModel):
        result: str

    # Act
    @lamina(schema_in=SchemaIn, schema_out=SchemaOut, content_type="application/json")
    async def handler(request: Request):
        await asyncio.sleep(0.1)
        return json.loads(request.data)

    # Assert
    assert handler.schema_in == SchemaIn
    assert handler.schema_out == SchemaOut
    assert handler.content_type == "application/json"
