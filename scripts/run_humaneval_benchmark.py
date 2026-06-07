# run_humaneval_benchmark.py
import subprocess
import os
import sys
import json
from convert_humaneval import prepare_benchmark_data

# 获取当前脚本所在目录（项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = sys.executable
MAIN_PATH = os.path.join(BASE_DIR, "main.py")

print(f"📌 项目根目录: {BASE_DIR}")
print(f"📌 使用 Python 解释器: {VENV_PYTHON}")


def find_generated_code_file(output_dir: str) -> str:
    """查找智能体生成的代码文件"""
    # 兼容处理：检查直接输出目录，或者智能体自建的子目录
    search_paths = [output_dir]
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isdir(item_path):
                search_paths.append(item_path)

    for path in search_paths:
        if not os.path.exists(path):
            continue
        try:
            files = os.listdir(path)
            # 优先精确查找 solution.py
            for f in files:
                if f.lower() == 'solution.py':
                    return os.path.join(path, f)
            # 其次查找任何包含业务代码的 python 文件 (排除测试文件)
            for f in files:
                if f.endswith('.py') and 'test' not in f.lower():
                    return os.path.join(path, f)
        except Exception:
            pass
    return None


def evaluate_solution(solution_code_path, eval_json_path, entry_point):
    """运行官方 HumanEval 测试用例检验最终代码"""
    if not os.path.exists(solution_code_path):
        return False, "未找到代码文件"

    try:
        with open(solution_code_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        with open(eval_json_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)

        test_script = eval_data["test"]

        # 构造执行隔离沙箱环境
        exec_globals = {}
        exec(code, exec_globals)

        # 建立映射
        if entry_point in exec_globals:
            exec_globals["candidate"] = exec_globals[entry_point]
        else:
            # 兜底尝试查找模糊匹配的函数
            found = None
            for key in exec_globals:
                if callable(exec_globals[key]) and not key.startswith('__'):
                    found = key
                    break
            if found:
                exec_globals["candidate"] = exec_globals[found]
            else:
                return False, f"代码中未找到入口函数: {entry_point}"

        # 运行官方盲测用例断言
        exec(test_script, exec_globals)
        return True, "✅ 通过官方用例"
    except AssertionError:
        return False, "❌ 未通过官方 Assert 断言验证"
    except Exception as e:
        return False, f"💥 运行时错误: {str(e)}"


def main():
    # 初始化数据
    print("🚀 正在初始化 HumanEval 10题 测试数据集...")
    test_cases = prepare_benchmark_data(limit=10)

    language = "Python"
    results = []
    passed_count = 0

    print(f"\n{'='*70}\n开始智能体 HumanEval 闭环性能测试 (语言: {language})\n{'='*70}")

    for clean_id, req_path, eval_path in test_cases:
        print("\n==================================================")
        print(f"▶️ [任务测试] {clean_id}")
        print("==================================================")

        output_dir = os.path.normpath(
            os.path.join(BASE_DIR, "outputs", "benchmark_results", language, clean_id)
        )

        # 确保系统环境带上强制强制编码标识
        current_env = os.environ.copy()
        current_env["PYTHONIOENCODING"] = "utf-8"

        # 1. 运行智能体图网络（需求 -> 设计 -> 代码 -> 测试 -> 修复）
        try:
            print("   🤖 智能体正在全生命周期运转中，请稍候...")
            result = subprocess.run(
                [VENV_PYTHON, MAIN_PATH, "--input", req_path, "--output", output_dir, "--language", language],
                cwd=BASE_DIR,
                capture_output=True,  # 捕获二进制流 bytes
                text=False,           # 🔥 关闭纯文本捕获，防止读取线程遇到中文系统错误码时崩溃
                timeout=180,
                env=current_env
            )

            # 🔥 采用宽容解码模式（对无法识别的字节用 ? 替代，确保主流程畅通无阻）
            stdout_str = result.stdout.decode('utf-8', errors='replace')
            stderr_str = result.stderr.decode('utf-8', errors='replace')

            print(f"   📊 智能体执行结束，退出码: {result.returncode}")

            # 如果退出码不为 0 或者没有成功生成代码，把日志打印出来看看智能体到底在卡在哪里
            if result.returncode != 0:
                print("   ⚠️ --- 智能体内部执行拦截日志 ---")
                if stderr_str.strip():
                    print(stderr_str[:800])
                if stdout_str.strip():
                    print("--- 业务流尾部输出 ---")
                    print(stdout_str[-800:])
                print("   ---------------------------------")
            else:
                print("   --- 🤖 智能体执行完毕，自测链路结束 ---")
                print(stdout_str[-600:].strip())
                print("   ---------------------------------------")

        except subprocess.TimeoutExpired:
            print("   ❌ 智能体全生命周期自测重试超时 (180秒)")
            results.append((clean_id, False, "超时"))
            continue
        except Exception as e:
            print(f"   ❌ 运行时发生异常: {e}")
            results.append((clean_id, False, str(e)))
            continue

        # 2. 评测系统接管：检查智能体产出的代码
        solution_file = find_generated_code_file(output_dir)

        with open(eval_path, 'r', encoding='utf-8') as f:
            eval_data = json.load(f)
            entry_point = eval_data.get("entry_point", "")

        is_correct, msg = evaluate_solution(solution_file, eval_path, entry_point)

        if is_correct:
            print(f"   🎯 最终判题结论: {msg}")
            results.append((clean_id, True, msg))
            passed_count += 1
        else:
            print(f"   🎯 最终判题结论: ❌ 失败 ({msg})")
            results.append((clean_id, False, msg))

    # 3. 打印最终总报告
    print(f"\n{'='*70}\n📊 HumanEval (10题) 项目需求→设计→代码→测试→修复 最终通过率报告\n{'='*70}")
    for idx, (name, status_bool, detail) in enumerate(results):
        status_str = "✅ 通过" if status_bool else "❌ 失败"
        print(f"[{idx+1:02d}] 任务: {name:<15} | 结果: {status_str:<5} | 详情: {detail}")

    accuracy = (passed_count / len(test_cases)) * 100
    print(f"{'='*70}")
    print("📈 最终效能核心指标 (Metrics):")
    print(f"   - 总抽样题数: {len(test_cases)}")
    print(f"   - 完美交付数: {passed_count}")
    print(f"   - 转化通过率 (Pass Rate): {accuracy:.2f}%")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
