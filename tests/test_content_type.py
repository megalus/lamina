import json

from lamina import Request, lamina
from lamina.helpers import Lamina


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
    @lamina(content_type=Lamina.HTML)
    def handler(request: Request):
        return "<h1>hello world</h1>"

    # Act
    response = handler({"body": '{"foo": "bar"}'}, None)

    # Assert
    assert response["statusCode"] == 200
    assert response["body"] == "<h1>hello world</h1>"
    assert response["headers"] == {"Content-Type": "text/html; charset=utf-8"}
