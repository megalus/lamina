import time

from lamina.helpers import async_


async def test_async_decorator():
    # Arrange
    def long_sync_process(value: int):
        time.sleep(0.1)
        return 100 + value

    async def handler():
        res = await async_(long_sync_process)(100)
        return res

    # Act
    result = await handler()

    # Assert
    assert result == 200
