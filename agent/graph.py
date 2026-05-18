# agent/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict, Any
import operator
import sys
import os

# 添加项目根目录到路径，方便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工具函数
from tools.file_tools import save_code
from tools.executor import run_pytest

# 导入 LLM 客户端（使用新的 generate_code_and_test）
from agent.llm_client import generate_code_and_test, fix_code


# 1. 定义状态
class AgentState(TypedDict):
    messages: Annotated[List[str], operator.add]
    steps: int
    code: str                    # 当前生成的代码
    test_code: str               # 测试代码
    test_result: Dict[str, Any]  # 测试结果
    requirement: str             # 用户需求
    output_dir: str

# 2. 创建图
workflow = StateGraph(AgentState)


# 3. 定义节点函数
def generate_code_node(state: AgentState) -> dict:
    """生成代码节点：同时生成代码和测试用例"""
    print("🟡 生成代码节点被调用")
    
    requirement = state.get("requirement", "")
    output_dir = state.get("output_dir", "output")  # 获取输出目录
    if not requirement:
        for msg in state.get("messages", []):
            if msg.startswith("需求:"):
                requirement = msg.replace("需求:", "").strip()
                break
    
    print(f"📝 需求: {requirement[:100]}...")
    print(f"📁 输出目录: {output_dir}")

    # 同时生成代码和测试
    code, test_code = generate_code_and_test(requirement)
    print(f"✅ 代码生成完成，长度: {len(code)} 字符")
    print(f"✅ 测试生成完成，长度: {len(test_code)} 字符")
    
    # 确保 output 目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存实现代码
    impl_filepath = os.path.join(output_dir, "solution.py")
    save_code(code, impl_filepath)
    
    # 保存测试代码
    test_filepath = os.path.join(output_dir, "test_solution.py")
    save_code(test_code, test_filepath)
    
    print(f"📁 代码已保存到: {impl_filepath}")
    print(f"📁 测试已保存到: {test_filepath}")
    
    return {
        "code": code,
        "test_code": test_code,
        "messages": ["代码和测试已生成并保存"],
        "steps": state.get("steps", 0) + 1
    }


def run_tests_node(state: AgentState) -> dict:
    """运行测试节点：执行pytest并收集结果"""
    print("🟡 运行测试节点被调用")


    output_dir = state.get("output_dir", "output")
    test_filepath = os.path.join(output_dir, "test_solution.py")
    
    # 调用接口函数运行测试
    result = run_pytest(test_filepath)

    # 打印完整错误信息
    print(result['output'])

    print(f"📊 测试结果: 通过={result['passed']}, 失败={result['failed']}")
    
    return {
        "test_result": result,
        "messages": [f"测试完成: 通过{result['passed']}个, 失败{result['failed']}个"]
    }


def fix_code_node(state: AgentState) -> dict:
    """修复代码节点：根据错误日志修复代码"""
    print("🟡 修复代码节点被调用")
    
    output_dir = state.get("output_dir", "output")

    fixed_code = fix_code(
        code=state.get("code", ""),
        error_log=state.get("test_result", {}).get("output", ""),
        test_code=state.get("test_code", ""),
        requirement=state.get("requirement", "")
    )
    
    # 保存修复后的代码
    filepath = os.path.join(output_dir, "solution.py")
    os.makedirs(output_dir, exist_ok=True)
    save_code(fixed_code, filepath)
    
    print(f"✅ 代码已修复，保存到: {filepath}")
    
    return {
        "code": fixed_code,
        "messages": ["代码已修复"],
        "steps": state.get("steps", 0) + 1
    }


# 4. 添加节点到图
workflow.add_node("generate_code", generate_code_node)
workflow.add_node("run_tests", run_tests_node)
workflow.add_node("fix_code", fix_code_node)


# 5. 定义边
workflow.set_entry_point("generate_code")
workflow.add_edge("generate_code", "run_tests")


# 6. 条件边：测试失败则去修复，通过则结束
def should_continue(state: AgentState) -> str:
    """判断测试结果，决定下一步"""
    test_result = state.get("test_result", {})
    steps = state.get("steps", 0)
    max_steps = 3  # 最多修复3次
    
    # 如果测试通过，结束
    if test_result.get("failed", 0) == 0:
        print("✅ 测试全部通过！任务完成")
        return "end"
    
    # 如果超过最大重试次数，结束
    if steps >= max_steps:
        print(f"⚠️ 已达到最大重试次数({max_steps})，停止修复")
        return "end"
    
    # 否则继续修复
    print("❌ 测试失败，进入修复流程...")
    return "fix_code"


workflow.add_conditional_edges("run_tests", should_continue, {
    "fix_code": "fix_code",
    "end": END
})

workflow.add_edge("fix_code", "run_tests")


# 7. 编译
app = workflow.compile()


# 8. 测试入口
if __name__ == "__main__":
    # 测试需求
    test_requirement = "写一个Python函数，输入两个数字，返回它们的和"
    
    print("=" * 50)
    print("开始测试智能体流程")
    print("=" * 50)
    
    result = app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": test_requirement
    })
    
    print("\n" + "=" * 50)
    print("执行完成")
    print(f"最终状态: steps={result.get('steps', 0)}")
    print(f"最终测试结果: {result.get('test_result', {})}")