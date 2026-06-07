# agent/code_runner.py
import os
import sys
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.graph import app

def run_code_from_uml_dir(
    input_dir: str, 
    output_dir: str = "./output", 
    language: str = "Python"
) -> Dict[str, Any]:
    """
    场景二：单独从包含 UML / 设计文档的目录中读取文件，作为输入生成代码
    """
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        
    compiled_requirement = "【根据以下设计模型与图表生成代码】\n\n"
    
    # 1. 尝试读取总体说明文档
    md_path = os.path.join(input_dir, "system_design.md")
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            compiled_requirement += f"### 设计方案报告 (Markdown):\n{f.read()}\n\n"
            
    # 2. 尝试读取类图
    class_puml = os.path.join(input_dir, "class_diagram.puml")
    if os.path.exists(class_puml):
        with open(class_puml, "r", encoding="utf-8") as f:
            compiled_requirement += f"### 类图结构 (PlantUML):\n```puml\n{f.read()}\n```\n\n"
            
    # 3. 尝试读取活动图
    activity_puml = os.path.join(input_dir, "activity_diagram.puml")
    if os.path.exists(activity_puml):
        with open(activity_puml, "r", encoding="utf-8") as f:
            compiled_requirement += f"### 业务活动图 (PlantUML):\n```puml\n{f.read()}\n```\n\n"

    # 如果什么 UML 文件都没找到，尝试降级读取普通的 txt 需求
    if len(compiled_requirement) < 50:
        txt_files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
        if txt_files:
            with open(os.path.join(input_dir, txt_files[0]), "r", encoding="utf-8") as f:
                compiled_requirement += f"### 基础PRD需求:\n{f.read()}"
        else:
            raise ValueError(f"在目录 {input_dir} 中未找到任何有效的 .puml, .md 或 .txt 需求文件！")

    print(f"🚀 已成功加载 UML/设计模型，准备启动组合 B 编码图工作流...")
    os.makedirs(output_dir, exist_ok=True)
    
    # 触发 LangGraph 的 code 任务
    return app.invoke({
        "messages": [f"从本地目录加载设计模型成功，启动独立编码流程。"],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": compiled_requirement,
        "output_dir": output_dir,
        "language": language,
        "task": "code", # 只走生成代码 + 测试自愈路线
        "design_models": {}
    })