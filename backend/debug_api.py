"""
Debug API to capture exactly what GUVI sends.
Run with: python -m backend.debug_api
Then expose with: ngrok http 8000
"""
from fastapi import FastAPI, Request, Header
from typing import Optional
import uvicorn
import json

app = FastAPI()

@app.post("/v1/chat")
async def debug_chat(request: Request, x_api_key: Optional[str] = Header(None, alias="x-api-key")):
    # Get raw body
    body = await request.body()
    
    # Get all headers
    headers = dict(request.headers)
    
    print("\n" + "="*60)
    print("🔍 INCOMING REQUEST FROM GUVI")
    print("="*60)
    print("\n📋 HEADERS:")
    for k, v in headers.items():
        print(f"  {k}: {v}")
    
    print(f"\n🔑 x-api-key: {x_api_key}")
    
    print("\n📦 RAW BODY:")
    print(body.decode('utf-8'))
    
    try:
        parsed = json.loads(body)
        print("\n📝 PARSED JSON:")
        print(json.dumps(parsed, indent=2))
    except:
        print("\n❌ Could not parse as JSON")
    
    print("="*60 + "\n")
    
    # Return expected format
    return {"status": "success", "reply": "Debug response - check terminal for request details"}

@app.get("/")
async def health():
    return {"status": "ok", "message": "Debug API running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    print("🚀 Starting Debug API on http://localhost:8000")
    print("💡 Expose with: ngrok http 8000")
    print("📋 Then use the ngrok URL in GUVI tester")
    uvicorn.run(app, host="0.0.0.0", port=8000)
