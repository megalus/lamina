import json

from lamina import Request, lamina


def test_403_response():
    # Arrange
    @lamina()
    def handler(request: Request):
        return (
            None,
            403,
            {"Location": "https://foo.bar"},
        )

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)

    # Assert
    assert response["statusCode"] == 403
    assert response["body"] is None
    assert response["headers"] == {
        "Content-Type": "text/html; charset=utf-8",
        "Location": "https://foo.bar",
    }


def test_get_handlers():
    # Arrange
    @lamina()
    def handler(request: Request):
        return request.headers

    # Simulate an AWS Lambda Event with common headers
    event = {
        "httpMethod": "GET",
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "UnitTestAgent/1.0",
            "Accept": "*/*",
        },
        "body": '{"test": "data"}',
    }

    # Act
    response = handler(event, None)
    headers = json.loads(response["body"])

    # Assert
    assert headers == {
        "Content-Type": "application/json",
        "User-Agent": "UnitTestAgent/1.0",
        "Accept": "*/*",
    }
