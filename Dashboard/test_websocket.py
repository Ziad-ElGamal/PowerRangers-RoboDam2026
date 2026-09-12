import asyncio
import websockets


async def test_websocket():

    uri = "ws://127.0.0.1:8000/ws"

    print("Connecting to WebSocket...")

    async with websockets.connect(uri) as websocket:

        print("Connected!")

        print("Waiting for telemetry payload...")

        message = await websocket.recv()

        print("\nReceived:")
        print(message)


asyncio.run(test_websocket())