import json

from lamina import Request, lamina


def test_default_code():
    # Arrange
    @lamina()
    def handler(request: Request):
        return json.loads(request.data)

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)

    # Assert
    assert response["statusCode"] == 200


def test_custom_code():
    # Arrange
    @lamina()
    def handler(request: Request):
        return json.loads(request.data), 418

    # Act
    response = handler({"body": '{"tea": "pot"}'}, None)

    # Assert
    assert response["statusCode"] == 418
