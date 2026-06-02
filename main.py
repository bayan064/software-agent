# main.py
import argparse
import os
import sys
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.graph import app


# ============================================================
# 函数式接口（供其他 Python 脚本或插件调用）
# ============================================================

def run_design_only(requirement: str, output_dir: str = "./output", format: str = "plantuml") -> Dict[str, Any]:
    """
    只运行设计模式（组合a）
    """
    os.makedirs(output_dir, exist_ok=True)
    
    return app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": requirement,
        "output_dir": output_dir,
        "language": "Python",  # 设计模式不需要语言，但保留
        "task": "design",
        "design_models": {}
    })


def run_code_only(requirement: str, output_dir: str = "./output", language: str = "Python") -> Dict[str, Any]:
    """
    只运行编码和测试模式（组合b）
    """
    os.makedirs(output_dir, exist_ok=True)
    
    return app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": requirement,
        "output_dir": output_dir,
        "language": language,
        "task": "code",
        "design_models": {}
    })


def run_fix_only(requirement: str, output_dir: str = "./output", language: str = "Python") -> Dict[str, Any]:
    """
    组合 C：独立自愈修复模式（新追加）
    直接读取输出目录下的现有代码，执行测试并进行修复循环
    """
    os.makedirs(output_dir, exist_ok=True)
    
    ext = "java" if language == "Java" else "py"
    impl_filename = f"Solution.{ext}" if language == "Java" else f"solution.{ext}"
    test_filename = f"TestSolution.{ext}" if language == "Java" else f"test_solution.{ext}"
    
    impl_path = os.path.join(output_dir, impl_filename)
    test_path = os.path.join(output_dir, test_filename)
    
    existing_code = ""
    existing_test = ""
    
    if os.path.exists(impl_path):
        with open(impl_path, "r", encoding="utf-8") as f:
            existing_code = f.read()
    if os.path.exists(test_path):
        with open(test_path, "r", encoding="utf-8") as f:
            existing_test = f.read()
            
    # 预先在本地默默执行一次跑测，获取真实的初始错误日志
    print("🔍 正在拉取当前代码的真实测试错误日志...")
    from tools.executor import run_pytest
    initial_res = run_pytest(test_path if os.path.exists(test_path) else impl_path, language=language)
    
    return app.invoke({
        "messages": [f"接收到待修复代码，启动组合 C 自愈流程。"],
        "steps": 0,
        "code": existing_code,
        "test_code": existing_test,
        "test_result": initial_res,
        "requirement": requirement,
        "output_dir": output_dir,
        "language": language,
        "task": "fix",
        "design_models": {}
    })


def run_full_workflow(requirement: str, output_dir: str = "./output", language: str = "Python") -> Dict[str, Any]:
    """
    运行完整流程（组合a + 组合b）
    """
    os.makedirs(output_dir, exist_ok=True)
    
    return app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": requirement,
        "output_dir": output_dir,
        "language": language,
        "task": "full",
        "design_models": {}
    })


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='LLM Based Software Engineering Agent CLI')
    
    parser.add_argument('--input', type=str, required=True, help='输入需求文件路径 (txt)')
    parser.add_argument('--output', type=str, default='./output', help='输出结果目录')
    # 在 choices 中追加 'fix'
    parser.add_argument('--task', type=str, default='full', choices=['design', 'code', 'fix', 'full'],
                        help='任务类型: design(组合A), code(组合B), fix(组合C), full(完整流程)')
    parser.add_argument('--language', type=str, default='Python', choices=['Python', 'Java'],
                        help='目标编程语言 (Python/Java)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ 错误: 输入需求文件不存在: {args.input}")
        sys.exit(1)
        
    with open(args.input, 'r', encoding='utf-8') as f:
        requirement = f.read().strip()
        
    print(f"🚀 智能体启动...")
    print(f"📋 任务类型: {args.task}")
    print(f"📝 编程语言: {args.language}")
    print(f"📂 输出目录: {args.output}")
    print(f"--- 需求内容预览 ---")
    print(requirement[:200] + ("..." if len(requirement) > 200 else ""))
    print(f"------------------")
    
    # 任务分发映射表中优雅追加 "fix" 路由
    task_handlers = {
        "design": lambda req, out, lang: run_design_only(req, out),
        "code": lambda req, out, lang: run_code_only(req, out, lang),
        "fix": lambda req, out, lang: run_fix_only(req, out, lang),  # 新增组合C处理器
        "full": lambda req, out, lang: run_full_workflow(req, out, lang)
    }
    
    handler = task_handlers.get(args.task)
    if not handler:
        print(f"❌ 未知任务类型: {args.task}")
        sys.exit(1)
        
    # 执行智能体图流程
    result = handler(requirement, args.output, args.language)
    
    # 漂亮的控制台输出结果打印展示
    print(f"\n✨ 智能体执行完毕！")
    
    design_models = result.get("design_models", {})
    if design_models:
        print(f"\n🎨 生成的设计模型:")
        if "class_diagram" in design_models and design_models["class_diagram"]:
            print(f"   - 类图: 已生成")
        if "activity_diagram" in design_models and design_models["activity_diagram"]:
            print(f"   - 活动图: 已生成")
        if "state_diagram" in design_models and design_models["state_diagram"]:
            print(f"   - 状态机图: 已生成")
        if "text_design" in design_models and design_models["text_design"]:
            print(f"   - 文本设计说明: 已生成")
            
    # 显示代码和测试结果
    if args.task != "design":
        test_result = result.get("test_result", {})
        print(f"\n📊 测试结果: 通过={test_result.get('passed', 0)}, 失败={test_result.get('failed', 0)}")
        print(f"🔄 修复次数: {result.get('steps', 0)}")
        
    print(f"\n📁 输出文件保存在: {args.output}")
    
    # 根据任务类型和测试结果返回退出码
    if args.task == "design":
        if design_models:
            print("\n✅ 设计模型生成成功！")
            sys.exit(0)
        else:
            print("\n❌ 设计模型生成失败")
            sys.exit(1)
    else:
        test_result = result.get("test_result", {})
        if test_result.get("failed", 0) == 0:
            print("\n✅ 智能体执行成功！所有测试通过")
            sys.exit(0)
        else:
            print("\n⚠️ 智能体执行完成，但部分测试未通过")
            sys.exit(1)


if __name__ == "__main__":
    main()