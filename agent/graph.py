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
    """组合 B：根据设计模型生成代码节点
    
    支持两种输入模式：
    1. 场景一（组合A->B联调）：从 state["design_models"] 中读取组合 A 生成的内存数据。
    2. 场景二（独立测试）：当 state["requirement"] 传入的是一个本地文件夹路径时，
                           自动扫描并读取该文件夹下的 UML 文件（.puml / .md）作为输入。
    """
    print("🟡 生成代码节点被调用")
    
    raw_requirement = state.get("requirement", "").strip()
    output_dir = state.get("output_dir", "output")
    language = state.get("language", "Python")
    
    # 兜底旧逻辑：如果 requirement 为空，尝试从 messages 恢复
    if not raw_requirement:
        for msg in state.get("messages", []):
            if msg.startswith("需求:"):
                raw_requirement = msg.replace("需求:", "").strip()
                break
                
    compiled_context = ""
    
    # =========================================================================
    # 核心改动：支持【场景二】单独在 test/requirement 中读取本地文件夹下的 UML 文件
    # =========================================================================
    if os.path.isdir(raw_requirement):
        input_dir = raw_requirement
        print(f"📂 检测到 requirement 为本地目录，正在从 {input_dir} 加载 UML 设计图与文档进行独立测试...")
        compiled_context += "【从测试目录读取到的设计模型与 UML】:\n"
        
        # 1. 读取总体架构设计说明
        md_path = os.path.join(input_dir, "system_design.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    compiled_context += f"\n- 架构设计说明报告:\n{f.read().strip()}\n"
            except OSError as e:
                print(f"⚠️ 读取 system_design.md 失败: {e}")
                
        # 2. 读取 PlantUML 类图
        class_puml = os.path.join(input_dir, "class_diagram.puml")
        if os.path.exists(class_puml):
            try:
                with open(class_puml, "r", encoding="utf-8") as f:
                    compiled_context += f"\n- 类图结构 (PlantUML):\n```puml\n{f.read().strip()}\n```\n"
            except OSError as e:
                print(f"⚠️ 读取 class_diagram.puml 失败: {e}")
                
        # 3. 读取 PlantUML 业务流程/活动图
        activity_puml = os.path.join(input_dir, "activity_diagram.puml")
        if os.path.exists(activity_puml):
            try:
                with open(activity_puml, "r", encoding="utf-8") as f:
                    compiled_context += f"\n- 业务活动图/流程图 (PlantUML):\n```puml\n{f.read().strip()}\n```\n"
            except OSError as e:
                print(f"⚠️ 读取 activity_diagram.puml 失败: {e}")

        # 如果是个目录，但里面啥模型都没有，就把目录名或者原本的提示作为基础
        final_prompt = compiled_context if len(compiled_context) > 30 else f"基于该模块的设计模型生成代码。目标目录: {input_dir}"
        
    else:
        # =========================================================================
        # 保留并增强【场景一】联调逻辑（接收组合A传过来的内存字典数据）
        # =========================================================================
        final_prompt = raw_requirement
        
        # 兼容你原有的 docs/test_cases.md 读取逻辑
        if "文档" in final_prompt:
            doc_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "test_cases.md")
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    doc_content = f.read().strip()
                if doc_content:
                    final_prompt = f"{final_prompt}\n\n【文档内容】\n{doc_content}"
            except OSError:
                print("⚠️ 未能读取 docs/test_cases.md，按原需求继续")
                
        # 从组合 A 传递的内存字典中提取更完整的 UML 数据
        design_models = state.get("design_models", {})
        if design_models:
            added_context = ""
            if design_models.get("text_design"):
                added_context += f"\n【参考架构设计说明】:\n{design_models.get('text_design')}\n"
            if design_models.get("class_diagram"):
                added_context += f"\n【类图定义 (PlantUML)】:\n```puml\n{design_models.get('class_diagram')}\n```\n"
            if design_models.get("activity_diagram"):
                added_context += f"\n【业务流程图 (PlantUML)】:\n```puml\n{design_models.get('activity_diagram')}\n```\n"
                
            if added_context:
                final_prompt = f"{final_prompt}\n\n=== 补充组合A设计模型上下文 ==={added_context}"

    print(f"📝 最终喂给 LLM 的上下文前 100 字: {final_prompt[:100]}...")
    print(f"📁 输出目录: {output_dir}")

    # 调用大模型生成代码和单元测试
    code, test_code = generate_code_and_test(final_prompt, language)
    
    # 保持你原有的文件保存和状态返回逻辑
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
    elif task == "fix":
        # 组合 C 核心：如果已经有了测试结果和报错信息，直接送去 fix_code 修复
        test_result = state.get("test_result", {})
        if test_result.get("failed", 0) > 0:
            return "fix_code"
        return "run_tests" # 否则先测一下看看错在哪
    else: # full 流程先生成设计
        return "generate_design"

workflow.set_conditional_entry_point(router_start, {
    "generate_design": "generate_design",
    "generate_code": "generate_code",
    "fix_code": "fix_code",
    "run_tests": "run_tests"
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