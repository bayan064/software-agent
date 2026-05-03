# agent/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator

# 1. 定义状态（冰箱里的东西）
class AgentState(TypedDict):
    messages: Annotated[List[str], operator.add]
    steps: int

# 2. 创建图
workflow = StateGraph(AgentState)

# 3. 定义节点（先写占位函数）
def generate_code(state: AgentState) -> dict:
    """生成代码节点（暂时只打印，后面替换成真实LLM调用）"""
    print("🟡 生成代码节点被调用")
    # TODO: 调用 llm_client.generate_code
    return {"messages": ["生成了代码"]}

def run_tests(state: AgentState) -> dict:
    """运行测试节点（暂时只打印，后面替换成真实测试调用）"""
    print("🟡 运行测试节点被调用")
    # TODO: 调用 tools/ 里的 run_pytest 函数
    return {"messages": ["测试运行完成"]}

def fix_code(state: AgentState) -> dict:
    """修复代码节点（暂时只打印，后面替换成真实修复逻辑）"""
    print("🟡 修复代码节点被调用")
    # TODO: 调用 llm_client.fix_code
    return {"messages": ["修复了代码"]}

# 4. 添加节点到图
workflow.add_node("generate_code", generate_code)
workflow.add_node("run_tests", run_tests)
workflow.add_node("fix_code", fix_code)

# 5. 定义边（路径怎么走）
workflow.set_entry_point("generate_code")
workflow.add_edge("generate_code", "run_tests")

# 6. 条件边：测试失败则去修复，通过则结束
def should_continue(state: AgentState) -> str:
    """判断测试结果"""
    # TODO: 根据实际测试结果返回 "fix_code" 或 "end"
    return "end"  # 暂时默认结束

workflow.add_conditional_edges("run_tests", should_continue, {
    "fix_code": "fix_code",
    "end": END
})

workflow.add_edge("fix_code", "run_tests")

# 7. 编译
app = workflow.compile()

# 8. 测试空壳
if __name__ == "__main__":
    result = app.invoke({"messages": [], "steps": 0})
    print("执行结果:", result)