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
    language: str   

def get_file_extension(language: str) -> tuple:
    """根据语言返回文件扩展名和测试文件扩展名"""
    if language == "Java":
        return "java", "java"
    else:  # Python
        return "py", "py"


def get_test_runner(language: str) -> str:
    """返回测试运行器名称"""
    return "pytest" if language == "Python" else "junit"

# 2. 创建图
workflow = StateGraph(AgentState)


# 3. 定义节点函数
def generate_code_node(state: AgentState) -> dict:
    """生成代码节点：同时生成代码和测试用例"""
    print("🟡 生成代码节点被调用")
    
    requirement = state.get("requirement", "")
    output_dir = state.get("output_dir", "output")  # 获取输出目录
    language = state.get("language", "Python")


    if not requirement:
        for msg in state.get("messages", []):
            if msg.startswith("需求:"):
                requirement = msg.replace("需求:", "").strip()
                break
    
    print(f"📝 需求: {requirement[:100]}...")
    print(f"📁 输出目录: {output_dir}")
    print(f"💻 目标语言: {language}")

    #根据语言 同时生成代码和测试
    code, test_code = generate_code_and_test(requirement,language)
    print(f"✅ 代码生成完成，长度: {len(code)} 字符")
    print(f"✅ 测试生成完成，长度: {len(test_code)} 字符")
    
    # 确保 output 目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 根据语言选择文件扩展名
    ext, test_ext = get_file_extension(language)
    
    # 保存实现代码
    impl_filename = f"Solution.{ext}" if language == "Java" else f"solution.{ext}"
    impl_filepath = os.path.join(output_dir, impl_filename)
    save_code(code, impl_filepath)

    # 保存测试代码
    test_filename = f"TestSolution.{test_ext}" if language == "Java" else f"test_solution.{test_ext}"
    test_filepath = os.path.join(output_dir, test_filename)
    save_code(test_code, test_filepath)
    
    print(f"📁 代码已保存到: {impl_filepath}")
    print(f"📁 测试已保存到: {test_filepath}")
    
    return {
        "code": code,
        "test_code": test_code,
        "messages": [f"{language}代码和测试已生成并保存"],
        "steps": state.get("steps", 0) + 1
    }


def run_tests_node(state: AgentState) -> dict:
    """运行测试节点：执行pytest并收集结果"""
    print("🟡 运行测试节点被调用")


    output_dir = state.get("output_dir", "output")
    language = state.get("language", "Python")

     # 根据语言构建测试文件路径
    if language == "Java":
        test_filepath = os.path.join(output_dir, "TestSolution.java")
    else:  # Python
        test_filepath = os.path.join(output_dir, "test_solution.py")
    
    # 检查测试文件是否存在
    if not os.path.exists(test_filepath):
        error_msg = f"测试文件不存在: {test_filepath}"
        print(f"❌ {error_msg}")
        return {
            "test_result": {
                "passed": 0,
                "failed": 1,
                "output": error_msg,
                "returncode": -1
            },
            "messages": [error_msg]
        }

    # 调用接口函数运行测试，传入语言参数
    result = run_pytest(test_filepath, language=language)

    # 打印输出（限制长度）
    output_preview = result['output'][-1000:] if len(result['output']) > 1000 else result['output']
    print(output_preview)

    print(f"📊 测试结果: 通过={result['passed']}, 失败={result['failed']}")
    print(f"📊 返回码: {result['returncode']}")

    return {
        "test_result": result,
        "messages": [f"测试完成: 通过{result['passed']}个, 失败{result['failed']}个"]
    }


def fix_code_node(state: AgentState) -> dict:
    """修复代码节点：根据错误日志修复代码"""
    print("🟡 修复代码节点被调用")
    
    output_dir = state.get("output_dir", "output")
    language = state.get("language", "Python")
    
    # 根据语言选择要修复的文件
    if language == "Java":
        # 对于 Java，只修复 Solution.java
        current_code = state.get("code", "")
        error_log = state.get("test_result", {}).get("output", "")
        
        # 检查错误是否来自 Solution.java 中错误地包含了 import
        if "Solution.java" in error_log and "import" in error_log:
            # 清理当前代码，移除可能的 import 语句
            lines = current_code.split('\n')
            cleaned_lines = [line for line in lines if not line.strip().startswith('import ')]
            current_code = '\n'.join(cleaned_lines)
            print("🧹 已清理 Solution.java 中的错误 import 语句")
        
        fixed_code = fix_code(
            code=current_code,
            error_log=error_log,
            test_code=state.get("test_code", ""),
            requirement=state.get("requirement", ""),
            language=language
        )
    else:
        fixed_code = fix_code(
            code=state.get("code", ""),
            error_log=state.get("test_result", {}).get("output", ""),
            test_code=state.get("test_code", ""),
            requirement=state.get("requirement", ""),
            language=language
        )
    
    # 保存修复后的代码
    ext, _ = get_file_extension(language)
    impl_filename = f"Solution.{ext}" if language == "Java" else f"solution.{ext}"
    filepath = os.path.join(output_dir, impl_filename)
    os.makedirs(output_dir, exist_ok=True)
    save_code(fixed_code, filepath)
    
    print(f"✅ 代码已修复，保存到: {filepath}")
    
    return {
        "code": fixed_code,
        "messages": [f"{language}代码已修复"],
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
    
    for lang in ["Python", "Java"]:
        print("=" * 50)
        print(f"测试 {lang} 语言")
        print("=" * 50)


    result = app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": test_requirement,
        "output_dir": f"test_output_{lang.lower()}",
        "language": lang
    })
    
    print("\n" + "=" * 50)
    print("执行完成")
    print(f"最终状态: steps={result.get('steps', 0)}")
    print(f"最终测试结果: {result.get('test_result', {})}")