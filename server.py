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
    history: List[Dict[str, str]] = []
    language: str = "Python"
    task: str = "full"

class DesignRequest(BaseModel):
    design: dict  # 新增

async def stream_response(requirement: str, history: List[Dict[str, str]] = [], language: str = "Python", task: str = "full"):
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
    
    if task == "design":
        system_prompt = f"\n\n【重要系统指令】\n当前任务模式：仅设计(UML)。请输出 Markdown 格式的设计文档和 PlantUML 代码，绝对不要生成任何具体的编程语言（如Python/Java）代码。"
    else:
        system_prompt = f"\n\n【重要系统指令】\n当前任务模式：{task}。请严格使用【{language}】语言来编写代码。"
    
    full_requirement += system_prompt

    # 调用 agent
    result = app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": full_requirement,
        "language": language, 
        "task": task
    })
    
    code = result.get("code", "")
    design_data = result.get("design_models")
    
    if not design_data:
        output_dir = "output"

        design_data = {
            "text_design": "",
            "class_diagram": "",
            "activity_diagram": ""
        }

        md_file = os.path.join(output_dir, "system_design.md")
        if os.path.exists(md_file):
            design_data["text_design"] = open(
                md_file,
                "r",
                encoding="utf-8"
            ).read()

        class_file = os.path.join(output_dir, "class_diagram.puml")
        if os.path.exists(class_file):
            design_data["class_diagram"] = open(
                class_file,
                "r",
                encoding="utf-8"
            ).read()

        activity_file = os.path.join(output_dir, "activity_diagram.puml")
        if os.path.exists(activity_file):
            design_data["activity_diagram"] = open(
                activity_file,
                "r",
                encoding="utf-8"
            ).read()

    if design_data:
        # 发送设计提案格式
        yield f"""data: {json.dumps({
            'type': 'design_proposal',
            'title': '系统设计模型',
            'description': design_data.get('text_design', ''),
            'architecture': design_data.get('class_diagram', ''),
            'components': [design_data.get('activity_diagram', '')] if design_data.get('activity_diagram') else [],
            'pending': True
        })}\n\n"""
        
        # 如果只需要设计，直接发送完成信号并结束
        if task == "design":
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            yield "data: [DONE]\n\n"
            return
    
    # 流式输出代码
    for char in code:
        yield f"data: {json.dumps({'type': 'code_chunk', 'content': char, 'isCode': True})}\n\n"
        await asyncio.sleep(0.01)
    
    yield f"data: {json.dumps({'type': 'complete', 'code': code})}\n\n"
    yield "data: [DONE]\n\n"

@api.post("/stream")
async def stream_generate(request: Request):
    return StreamingResponse(
        stream_response(request.requirement, request.history, request.language, request.task),
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
        "requirement": request.requirement,
        "language": request.language, 
        "task": request.task
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