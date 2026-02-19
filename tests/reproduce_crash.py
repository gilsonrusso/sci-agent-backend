import asyncio
import logging
from ypy_websocket.yroom import YRoom

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_room():
    print("Creating YRoom...")
    room = YRoom()

    # Start room background task
    print("Starting YRoom in background...")
    room_task = asyncio.create_task(room.start())

    # Give it a tiny bit to start up
    await asyncio.sleep(0.1)

    print("Modifying YDoc concurrently...")

    def modify(txn):
        ytext = txn.get_text("codemirror")
        ytext.extend(txn, "Hello World")

    try:
        room.ydoc.transact(modify)
        print("YDoc modified successfully.")
    except Exception as e:
        logger.exception("Modification failed!")

    await asyncio.sleep(2)
    print("Stopping room...")
    room_task.cancel()
    try:
        await room_task
    except asyncio.CancelledError:
        print("Room stopped.")
    except Exception as e:
        logger.exception("Room crashed during run!")


if __name__ == "__main__":
    try:
        asyncio.run(test_room())
    except KeyboardInterrupt:
        print("Stopped by user")
