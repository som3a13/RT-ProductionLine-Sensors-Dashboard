"""
Simple test script to verify WebSocket server is working
"""
import asyncio
import websockets
import json


async def test_connection():
    """Test WebSocket connection"""
    uri = "ws://localhost:8080"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            print(f"Received: {welcome}")
            
            # Send authentication
            auth_msg = {
                "type": "auth",
                "username": "admin",
                "password": "admin123"
            }
            await websocket.send(json.dumps(auth_msg))
            print("Sent authentication...")
            
            # Wait for response
            response = await websocket.recv()
            print(f"Response: {response}")
            
            # Send a command
            command_msg = {
                "type": "command",
                "command": "get_status",
                "data": {}
            }
            await websocket.send(json.dumps(command_msg))
            print("Sent get_status command...")
            
            # Wait for response
            response = await websocket.recv()
            print(f"Status response: {response}")
            
            print("Test completed successfully!")
            
    except ConnectionRefusedError:
        print("ERROR: Could not connect to WebSocket server.")
        print("Make sure the main application is running and the remote console is enabled.")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test_connection())

