import asyncio
import json

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
