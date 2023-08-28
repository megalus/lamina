from typing import Dict

from pydantic import BaseModel

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
