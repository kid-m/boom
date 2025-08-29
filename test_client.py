import asyncio
import websockets
import json


async def test_websocket_connection():
    game_id = "1"
    player_id = "player_0"
    uri = f"ws://127.0.0.1:8000/ws/{game_id}/{player_id}"

    print("Attempting to connect...")

    try:
        async with websockets.connect(uri) as websocket:
            print(
                f"Connected to WebSocket for Game ID: {game_id}, Player ID: {player_id}"
            )

            # Listen for the initial game state from the server
            initial_state_json = await websocket.recv()
            initial_state = json.loads(initial_state_json)
            print("Received initial game state:")
            print(json.dumps(initial_state, indent=2))

            # Send a test message to the server
            test_message = "Hello, server!"
            await websocket.send(test_message)
            print(f"\nSent message: '{test_message}'")

            # Listen for the server's response to our message
            response = await websocket.recv()
            print(f"Received server response: '{response}'")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket_connection())
