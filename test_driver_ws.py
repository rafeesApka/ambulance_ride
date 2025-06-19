import asyncio
import websockets
import json
import base64

async def test_driver_ws():
    uri = "ws://localhost:8000/ws/driver/2"
    # uri = "ws://13.203.89.173:8001/ws/driver/17"
    async with websockets.connect(uri) as websocket:
        print("Connected as driver 2")
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received from user {data['user_id']}: {data['message']}")
            for img in data.get("images", []):
                filename = f"received_{img['filename']}"
                with open(filename, "wb") as f:
                    f.write(base64.b64decode(img["data"]))
                print(f"Saved image: {filename}")

asyncio.run(test_driver_ws())
