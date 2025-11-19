import json

from lamina import Request, lamina


def test_json_response():
    # Arrange
    @lamina()
    def handler(request: Request):
        return json.loads(request.data)

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)

    # Assert
    assert response["statusCode"] == 200
    assert response["body"] == '{"foo": "bar"}'
    assert response["headers"] == {"Content-Type": "application/json; charset=utf-8"}


def test_html_response():
    # Arrange
    @lamina()
    def handler(request: Request):
        return "<html><h1>hello world</h1></html>"

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)

    # Assert
    assert response["statusCode"] == 200
    assert response["body"] == "<html><h1>hello world</h1></html>"
    assert response["headers"] == {"Content-Type": "text/html; charset=utf-8"}


def test_force_content_type():
    # Arrange
    @lamina(produces="text/plain")
    def handler(request: Request):
        return "<html><h1>hello world</h1></html>"

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)

    # Assert
    assert response["statusCode"] == 200
    assert response["body"] == "<html><h1>hello world</h1></html>"
    assert response["headers"] == {"Content-Type": "text/plain"}
