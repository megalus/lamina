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
