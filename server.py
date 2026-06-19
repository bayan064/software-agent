# server.py
import uvicorn
import json  # 新增
import asyncio  # 新增
import os
from typing import List, Dict

from typing import List, Dict
from fastapi.responses import StreamingResponse  # 新增
from fastapi import FastAPI
from pydantic import BaseModel
from agent.graph import app
api = FastAPI()

class Request(BaseModel):
    requirement: str
    history: List[Dict[str, str]] = []  # 新增历史消息字段

class DesignRequest(BaseModel):
    design: dict  # 新增

async def stream_response(requirement: str, history: List[Dict[str, str]] = []):
    """流式响应生成器，支持历史对话"""
    
    # 构建包含历史的完整需求
    full_requirement = requirement
    
    # 如果有历史对话，添加到上下文中
    if history:
        context = "\n\n【历史对话】\n"
        for msg in history:
            role = "用户" if msg["role"] == "user" else "助手"
            context += f"{role}: {msg['content']}\n"
        full_requirement = context + f"\n【当前问题】\n{requirement}"
    
    # 调用 agent
    result = app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": full_requirement
    })
    
    code = result.get("code", "")
    
    # 流式输出代码
    for char in code:
        yield f"data: {json.dumps({'type': 'code_chunk', 'content': char, 'isCode': True})}\n\n"
        await asyncio.sleep(0.01)
    
    yield f"data: {json.dumps({'type': 'complete', 'code': code})}\n\n"
    yield "data: [DONE]\n\n"

@api.post("/stream")
async def stream_generate(request: Request):
    return StreamingResponse(
        stream_response(request.requirement, request.history),
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
        "test_result": result.get("test_result"),
        "design_models": result.get("design_models")
    }

if __name__ == "__main__":
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run(api, host=host, port=port)