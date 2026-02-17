import asyncio
import sys
import subprocess
import time
import requests
import websockets
from ypy_websocket.yutils import YMessageType, YSyncMessageType, create_update_message
import y_py as Y

# Define constants
BASE_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/api/v1/editor/123e4567-e89b-12d3-a456-426614174000/ws/test-room"


async def run_test():
    print("starting uvicorn...")
    # Start uvicorn on port 8001 to avoid conflict
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/gilson-russo/development/professional/sci-agent-repositories/sci-agent-backend",
    )

    try:
        # Wait for server
        for _ in range(10):
            try:
                requests.get(BASE_URL)
                break
            except requests.ConnectionError:
                time.sleep(1)
                print("waiting for server...")
        else:
            print("Server failed to start")
            return

        print("Server up. Connecting Client A...")
        async with websockets.connect(WS_URL) as ws_a:
            print("Client A connected.")
            # Consume sync step 1
            msg = await ws_a.recv()

            print("Connecting Client B...")
            async with websockets.connect(WS_URL) as ws_b:
                print("Client B connected.")
                msg_b = await ws_b.recv()

                # Client A sends update
                print("Client A sending update...")
                ydoc = Y.YDoc()
                text = ydoc.get_text("codemirror")
                with ydoc.begin_transaction() as txn:
                    text.insert(txn, 0, "TEST")
                update = Y.encode_state_as_update(ydoc)
                msg_update = create_update_message(update)
                await ws_a.send(msg_update)
                print("Update sent.")

                # Client B should receive
                print("Client B waiting for update...")
                try:
                    update_b = await asyncio.wait_for(ws_b.recv(), timeout=5.0)
                    if (
                        update_b[0] == YMessageType.SYNC
                        and update_b[1] == YSyncMessageType.SYNC_UPDATE
                    ):
                        print("SUCCESS: Broadcast received!")
                    else:
                        print("FAILURE: Received unexpected message")
                except asyncio.TimeoutError:
                    print("FAILURE: Timed out waiting for broadcast")

    except Exception as e:
        print(f"Test Error: {e}")
    finally:
        proc.terminate()
        try:
            outs, errs = proc.communicate(timeout=2)
        except:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(run_test())
