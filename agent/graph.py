# agent/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict, Any
import operator
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.file_tools import save_code
from tools.executor import run_pytest

# 引入新写的设计生成函数
from agent.llm_client import generate_code_and_test, fix_code, generate_design_models


# 1. 定义状态 (确保兼容 task 和 design_models)
class AgentState(TypedDict):
    messages: Annotated[List[str], operator.add]
    steps: int
    code: str                    # 当前生成的代码
    test_code: str               # 测试代码
    test_result: Dict[str, Any]  # 测试结果
    requirement: str             # 用户需求
    output_dir: str
    language: str   
    task: str                    # 任务类型: "design", "code", "full"
    design_models: Dict[str, Any] # 存放设计模型的字典


def get_file_extension(language: str) -> tuple:
    if language == "Java":
        return "java", "java"
    else:
        return "py", "py"


# 2. 创建图
workflow = StateGraph(AgentState)


# ============================================================
# 3. 定义节点函数
# ============================================================

def generate_design_node(state: AgentState) -> dict:
    """组合 A：生成系统分析与设计模型节点"""
    print("🟡 生成系统设计模型节点被调用")
    requirement = state.get("requirement", "")
    output_dir = state.get("output_dir", "output")
    
    # 调用大模型生成图表
    models = generate_design_models(requirement)
    
    # 确保目录存在并保存对应的 PlantUML 模型及说明文件
    os.makedirs(output_dir, exist_ok=True)
    
    if models["class_diagram"]:
        save_code(models["class_diagram"], os.path.join(output_dir, "class_diagram.puml"))
    if models["activity_diagram"]:
        save_code(models["activity_diagram"], os.path.join(output_dir, "activity_diagram.puml"))
        
    # 合并成总体的 Markdown 文档供用户查阅
    doc_content = f"# 系统设计方案报告\n\n## 1. 概念与类图设计\n```puml\n{models['class_diagram']}\n```\n\n" \
                  f"## 2. 业务流程与活动图设计\n```puml\n{models['activity_diagram']}\n```\n\n" \
                  f"## 3. 设计决策与系统说明\n{models['text_design']}\n"
    save_code(doc_content, os.path.join(output_dir, "system_design.md"))
    
    print(f"✅ 设计模型已保存至目录: {output_dir}")
    return {
        "design_models": models,
        "messages": ["系统类图、活动图及说明文档已生成并保存。"]
    }


def generate_code_node(state: AgentState) -> dict:
    """组合 B：生成代码节点"""
    print("🟡 生成代码节点被调用")
    
    requirement = state.get("requirement", "")
    output_dir = state.get("output_dir", "output")
    language = state.get("language", "Python")

    # 如果有先前步骤生成的设计模型，将其作为上下文喂给代码生成，能够提高代码鲁棒性！
    design_models = state.get("design_models", {})
    if design_models and design_models.get("text_design"):
        requirement = f"{requirement}\n\n【参考架构设计说明】:\n{design_models.get('text_design')}"

    code, test_code = generate_code_and_test(requirement, language)
    
    os.makedirs(output_dir, exist_ok=True)
    ext, test_ext = get_file_extension(language)
    
    impl_filename = f"Solution.{ext}" if language == "Java" else f"solution.{ext}"
    impl_filepath = os.path.join(output_dir, impl_filename)
    save_code(code, impl_filepath)

    test_filename = f"TestSolution.{test_ext}" if language == "Java" else f"test_solution.{test_ext}"
    test_filepath = os.path.join(output_dir, test_filename)
    save_code(test_code, test_filepath)
    
    return {
        "code": code,
        "test_code": test_code,
        "messages": [f"{language} 代码和测试已完成生成"],
        "steps": state.get("steps", 0) + 1
    }


def run_tests_node(state: AgentState) -> dict:
    """运行测试节点"""
    print("🟡 运行测试节点被调用")
    output_dir = state.get("output_dir", "output")
    language = state.get("language", "Python")

    if language == "Java":
        test_filepath = os.path.join(output_dir, "TestSolution.java")
    else:
        test_filepath = os.path.join(output_dir, "test_solution.py")

    if not os.path.exists(test_filepath):
        error_msg = f"测试文件不存在: {test_filepath}"
        return {"test_result": {"passed": 0, "failed": 1, "output": error_msg, "returncode": -1}, "messages": [error_msg]}

    result = run_pytest(test_filepath, language=language)
    return {
        "test_result": result,
        "messages": [f"测试执行完毕: passed={result['passed']}, failed={result['failed']}"]
    }


def fix_code_node(state: AgentState) -> dict:
    """修复代码节点"""
    print("🟡 修复代码节点被调用")
    code = state.get("code", "")
    test_code = state.get("test_code", "")
    error_log = state.get("test_result", {}).get("output", "")
    requirement = state.get("requirement", "")
    language = state.get("language", "Python")
    output_dir = state.get("output_dir", "output")

    fixed = fix_code(code, error_log, test_code, requirement, language)
    
    ext, _ = get_file_extension(language)
    impl_filename = f"Solution.{ext}" if language == "Java" else f"solution.{ext}"
    save_code(fixed, os.path.join(output_dir, impl_filename))
    
    return {
        "code": fixed,
        "messages": ["代码已根据错误日志尝试进行修复"],
        "steps": state.get("steps", 0) + 1
    }


# ============================================================
# 4. 构建工作流拓扑结构与条件路由
# ============================================================

workflow.add_node("generate_design", generate_design_node)
workflow.add_node("generate_code", generate_code_node)
workflow.add_node("run_tests", run_tests_node)
workflow.add_node("fix_code", fix_code_node)


# 入口路由：根据任务类型决定第一步去哪里
def router_start(state: AgentState) -> str:
    task = state.get("task", "full")
    if task == "design":
        return "generate_design"
    elif task == "code":
        return "generate_code"
    else: # full 流程先生成设计
        return "generate_design"

workflow.set_conditional_entry_point(router_start, {
    "generate_design": "generate_design",
    "generate_code": "generate_code"
})


# 设计完后的过渡路由：如果是纯设计任务，到这就结束；如果是full流程，去生成代码
def router_after_design(state: AgentState) -> str:
    task = state.get("task", "full")
    if task == "design":
        return "end"
    else:
        return "generate_code"

workflow.add_conditional_edges("generate_design", router_after_design, {
    "generate_code": "generate_code",
    "end": END
})


# 测试完后的修复重试路由
def should_continue(state: AgentState) -> str:
    test_result = state.get("test_result", {})
    steps = state.get("steps", 0)
    max_steps = 3
    
    if test_result.get("failed", 0) == 0:
        print("✅ 测试全部通过！智能体任务圆满完成")
        return "end"
    
    if steps >= max_steps:
        print(f"⚠️ 已达到最大重试次数({max_steps})，强行停止修复")
        return "end"
    
    print("❌ 存在失败的单元测试用例，进入自愈修复流程...")
    return "fix_code"

workflow.add_conditional_edges("run_tests", should_continue, {
    "fix_code": "fix_code",
    "end": END
})

workflow.add_edge("generate_code", "run_tests")
workflow.add_edge("fix_code", "run_tests")

app = workflow.compile()