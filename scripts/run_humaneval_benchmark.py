# run_humaneval_benchmark.py
import subprocess
import os
import sys
import json
import argparse

# 获取当前脚本所在目录（项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = sys.executable
MAIN_PATH = os.path.join(BASE_DIR, "main.py")

print(f"📌 项目根目录: {BASE_DIR}")
print(f"📌 使用 Python 解释器: {VENV_PYTHON}")


def get_converter(language: str):
    """根据语言动态导入对应的转换器"""
    if language.lower() == "python":
        from convert_humaneval_python import prepare_benchmark_data
    else:
        from convert_humaneval_java import prepare_benchmark_data
    return prepare_benchmark_data


def find_generated_code_file(output_dir: str, language: str) -> str:
    """查找智能体生成的代码文件"""
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
            if language.lower() == "python":
                for f in files:
                    if f.lower() == 'solution.py':
                        return os.path.join(path, f)
                for f in files:
                    if f.endswith('.py') and 'test' not in f.lower():
                        return os.path.join(path, f)
            else:
                for f in files:
                    if f == 'Solution.java':
                        return os.path.join(path, f)
                for f in files:
                    if f.endswith('.java') and 'Test' not in f:
                        return os.path.join(path, f)
        except Exception:
            pass
    return None


def evaluate_solution_python(solution_code_path, eval_json_path, entry_point):
    """Python 版本的验证器"""
    if not os.path.exists(solution_code_path):
        return False, "未找到代码文件"

    try:
        with open(solution_code_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        with open(eval_json_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)

        test_script = eval_data["test"]

        exec_globals = {}
        exec(code, exec_globals)

        if entry_point in exec_globals:
            exec_globals["candidate"] = exec_globals[entry_point]
        else:
            found = None
            for key in exec_globals:
                if callable(exec_globals[key]) and not key.startswith('__'):
                    found = key
                    break
            if found:
                exec_globals["candidate"] = exec_globals[found]
            else:
                return False, f"代码中未找到入口函数: {entry_point}"

        exec(test_script, exec_globals)
        return True, "✅ 通过官方用例"
    except AssertionError:
        return False, "❌ 未通过官方 Assert 断言验证"
    except Exception as e:
        return False, f"💥 运行时错误: {str(e)}"


def evaluate_solution_java(solution_code_path, eval_json_path):
    """Java 版本的验证器"""
    if not os.path.exists(solution_code_path):
        return False, "未找到代码文件"
    
    try:
        # 确保 tools 目录在路径中
        tools_path = os.path.join(BASE_DIR, "tools")
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)
        
        from executor import run_java_tests
        
        result = run_java_tests(solution_code_path)
        
        if result['returncode'] == 0 and result['failed'] == 0:
            return True, "✅ 通过官方用例"
        else:
            return False, "❌ 测试失败"
            
    except Exception as e:
        return False, f"💥 Java 测试执行错误: {str(e)}"


def evaluate_solution(solution_code_path, eval_json_path, entry_point, language):
    """统一的验证器入口"""
    if language.lower() == "python":
        return evaluate_solution_python(solution_code_path, eval_json_path, entry_point)
    else:
        return evaluate_solution_java(solution_code_path, eval_json_path)


def main():
    parser = argparse.ArgumentParser(description='HumanEval 基准测试')
    parser.add_argument('--language', type=str, default='python', 
                        choices=['python', 'java'], 
                        help='编程语言 (python/java)')
    parser.add_argument('--limit', type=int, default=10, 
                        help='测试题目数量')
    args = parser.parse_args()
    
    # 根据语言获取对应的转换器
    prepare_func = get_converter(args.language)
    
    print(f"🚀 正在初始化 HumanEval {args.limit}题 测试数据集 (语言: {args.language})...")
    
    # 调用对应的转换器
    if args.language == "python":
        test_cases = prepare_func(limit=args.limit)
    else:
        test_cases = prepare_func(limit=args.limit, language=args.language)

    language = args.language
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

        current_env = os.environ.copy()
        current_env["PYTHONIOENCODING"] = "utf-8"

        try:
            print("   🤖 智能体正在全生命周期运转中，请稍候...")
            
            main_language = "Python" if language == "python" else "Java"
            
            result = subprocess.run(
                [VENV_PYTHON, MAIN_PATH, "--input", req_path, "--output", output_dir, "--language", main_language],
                cwd=BASE_DIR,
                capture_output=True,
                text=False,
                timeout=180,
                env=current_env
            )

            stdout_str = result.stdout.decode('utf-8', errors='replace')
            stderr_str = result.stderr.decode('utf-8', errors='replace')

            print(f"   📊 智能体执行结束，退出码: {result.returncode}")

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

        solution_file = find_generated_code_file(output_dir, language)

        with open(eval_path, 'r', encoding='utf-8') as f:
            eval_data = json.load(f)
            entry_point = eval_data.get("entry_point", "")

        is_correct, msg = evaluate_solution(solution_file, eval_path, entry_point, language)

        if is_correct:
            print(f"   🎯 最终判题结论: {msg}")
            results.append((clean_id, True, msg))
            passed_count += 1
        else:
            print(f"   🎯 最终判题结论: ❌ 失败 ({msg})")
            results.append((clean_id, False, msg))

    print(f"\n{'='*70}\n📊 HumanEval ({args.limit}题) 最终通过率报告\n{'='*70}")
    for idx, (name, status_bool, detail) in enumerate(results):
        status_str = "✅ 通过" if status_bool else "❌ 失败"
        print(f"[{idx+1:02d}] 任务: {name:<15} | 结果: {status_str:<5} | 详情: {detail}")

    if len(test_cases) > 0:
        accuracy = (passed_count / len(test_cases)) * 100
        print(f"{'='*70}")
        print("📈 最终效能核心指标 (Metrics):")
        print(f"   - 总抽样题数: {len(test_cases)}")
        print(f"   - 完美交付数: {passed_count}")
        print(f"   - 转化通过率 (Pass Rate): {accuracy:.2f}%")
        print(f"{'='*70}")
    else:
        print("❌ 没有成功加载任何测试用例")


if __name__ == "__main__":
    main()