import asyncio
from ypy_websocket.yroom import YRoom
import logging

logging.basicConfig(level=logging.INFO)


class MockWebSocket:
    def __init__(self):
        self.path = "/test"

    def __aiter__(self):
        return self

    async def __anext__(self):
        print("Called __anext__")
        await asyncio.sleep(1)
        return b"\x00\x00"

    async def send(self, msg):
        print(f"Called send: {msg}")

    async def recv(self):
        print("Called recv")
        await asyncio.sleep(1)  # Wait a bit
        return b"\x00\x00"


async def main():
    room = YRoom()
    mock_ws = MockWebSocket()
    print("Attempting to serve...")
    try:
        # Run serve for a short time
        await asyncio.wait_for(room.serve(mock_ws), timeout=2.0)
    except asyncio.TimeoutError:
        print("Serve ran fine (timed out as expected)")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
