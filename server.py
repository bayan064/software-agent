# server.py
import uvicorn
import json  # 新增
import asyncio  # 新增
import os
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
    
# ===== 核心改动：同时提取用户问题和代码结构 =====
    if history:
        user_questions = []
        code_structures = []  # 记录已有的类/函数名
        
        for msg in history:
            if msg["role"] == "user":
                content = msg.get("content", "").strip()
                if content:
                    if len(content) > 200:
                        content = content[:200] + "..."
                    user_questions.append(content)
            
            elif msg["role"] == "assistant":
                content = msg.get("content", "").strip()
                # 提取类名
                import re
                class_match = re.search(r'class\s+(\w+)', content)
                func_match = re.search(r'def\s+(\w+)', content)
                if class_match:
                    code_structures.append(f"类: {class_match.group(1)}")
                if func_match:
                    code_structures.append(f"函数: {func_match.group(1)}")
        
        # 构建上下文
        full_requirement = ""
        
        if user_questions:
            recent = user_questions[-3:] if len(user_questions) > 3 else user_questions
            history_context = "\n".join([f"- {q}" for q in recent])
            full_requirement += f"【历史对话回顾】\n{history_context}\n"
        
        if code_structures:
            # 去重
            unique_structures = list(set(code_structures))
            full_requirement += "\n【之前生成的代码结构】\n"
            for s in unique_structures:
                full_requirement += f"- {s}\n"
            full_requirement += "\n【重要】请在已有代码结构上新增或修改功能，保持代码一致性。\n"
        
        full_requirement += f"\n【当前需求】\n{requirement}"
    else:
        full_requirement = requirement
    
    if task == "design":
        system_prompt = "\n\n【重要系统指令】\n当前任务模式：仅设计(UML)。请输出 Markdown 格式的设计文档和 PlantUML 代码，绝对不要生成任何具体的编程语言（如Python/Java）代码。"
    else:
        system_prompt = "\n\n【重要系统指令】\n当前任务模式：{task}。请严格使用【{language}】语言来编写代码。"
    
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