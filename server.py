# server.py
from fastapi import FastAPI
from pydantic import BaseModel
from agent.graph import app
import uvicorn
from fastapi.responses import StreamingResponse  # 新增
import json  # 新增
import asyncio  # 新增

api = FastAPI()

class Request(BaseModel):
    requirement: str

class DesignRequest(BaseModel):
    design: dict  # 新增

async def stream_response(requirement: str):
    """流式响应生成器"""
    # 直接调用 agent 获取代码和测试
    result = app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": requirement
    })
    
    code = result.get("code", "")
    # 流式输出代码
    for char in code:
        yield f"data: {json.dumps({'type': 'code_chunk', 'content': char, 'isCode': True})}\n\n"
        await asyncio.sleep(0.01)
    
    # 完成信号
    yield f"data: {json.dumps({'type': 'complete', 'code': code})}\n\n"
    yield "data: [DONE]\n\n"

@api.post("/stream")
async def stream_generate(request: Request):
    return StreamingResponse(
        stream_response(request.requirement),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@api.post("/generate-code")
async def generate_code(request: DesignRequest):
    # 基于确认的设计方案生成代码
    # 这里可以调用 app.invoke 或者单独的代码生成逻辑
    result = app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": request.design.get("description", "")
    })
    return {
        "code": result.get("code"),
        "test_code": result.get("test_code")
    }

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