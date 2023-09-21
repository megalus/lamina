from lamina import lamina, Request
from lamina.helpers import Lamina


def test_403_response():
    # Arrange
    @lamina(content_type=Lamina.HTML)
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
    assert response["body"] == None
    assert response["headers"] == {
        "Content-Type": "text/html; charset=utf-8",
        "Location": "https://foo.bar",
    }
