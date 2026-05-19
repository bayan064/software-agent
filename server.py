# server.py
from fastapi import FastAPI
from pydantic import BaseModel
from agent.graph import app
import uvicorn

api = FastAPI()

class Request(BaseModel):
    requirement: str

@api.post("/generate")
async def generate(request: Request):
    result = app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": request.requirement
    })
    return {
        "code": result.get("code"),
        "test_code": result.get("test_code"),
        "test_result": result.get("test_result")
    }

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)