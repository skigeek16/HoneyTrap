import asyncio
import websockets
import httpx
import json
import os

API_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/session"

async def test_flow():
    session_id = "test-session-002"
    
    print(f"Connecting to WebSocket for session {session_id}...")
    try:
        async with websockets.connect(f"{WS_URL}/{session_id}") as websocket:
            
            # 2. Receive initial ACK
            ack = await websocket.recv()
            print(f"Received WS: {ack}")
            
            # 3. Send a chat message via HTTP
            print("Sending POST /v1/chat request...")
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{API_URL}/v1/chat",
                    json={"sessionId": session_id, "message": "I want to offer you a job making $5000 a week. Send bank details."}
                )
                print(f"HTTP Response: {resp.status_code} - {resp.json()}")
                
            # 4. Wait for SCAM_STATUS_UPDATE
            print("Waiting for Scam Status...")
            event1 = await websocket.recv()
            data1 = json.loads(event1)
            print(f"Received Event 1: {data1['type']}")
            print(f"Payload: {json.dumps(data1['payload'], indent=2)}")
            
            # 5. Wait for STALL_MESSAGE
            print("Waiting for Stall Message...")
            event2 = await websocket.recv()
            data2 = json.loads(event2)
            print(f"Received Event 2: {data2['type']}")
            print(f"Payload: {json.dumps(data2['payload'], indent=2)}")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_flow())
