import subprocess
import os
import sys

# 获取当前脚本所在目录（项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = sys.executable
MAIN_PATH = os.path.join(BASE_DIR, "main.py")

print(f"项目根目录: {BASE_DIR}")
print(f"使用Python: {VENV_PYTHON}")

test_cases = [
    ("有效的括号", "tests/requirements/req_valid_parentheses.txt"),      # Easy
    ("三数之和", "tests/requirements/req_three_sum.txt"),                # Medium
    ("合并K个有序链表", "tests/requirements/req_merge_k_lists.txt"),     # Hard
    ("柱状图中最大的矩形", "tests/requirements/req_largest_rectangle.txt"), # Hard
    ("滑动窗口最大值", "tests/requirements/req_sliding_window_max.txt"),  # Hard
]

# 支持的语言
languages = ["Python", "Java"]

for language in languages:
    print(f"\n{'='*50}")
    print(f"测试语言: {language}")
    print(f"{'='*50}")

    results = []

    for name, req_file in test_cases:
        print(f"\n测试: {name}")

        req_path = os.path.join(BASE_DIR, req_file)
        output_dir = os.path.join(BASE_DIR, "outputs", "benchmark_results", language, name)

        # 检查需求文件
        if not os.path.exists(req_path):
            print(f"❌ 需求文件不存在: {req_path}")
            results.append((name, "❌ 文件缺失"))
            continue

        print(f"需求文件: {req_path}")
        print(f"输出目录: {output_dir}")

        # 运行智能体
        try:
            result = subprocess.run(
                [VENV_PYTHON, MAIN_PATH, "--input", req_path, "--output", output_dir, "--language", language],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,
                env=os.environ.copy()
            )

            print(f"返回码: {result.returncode}")

            # 打印输出（调试用）
            if result.stdout:
                print(result.stdout[-500:])

            if result.stderr and "Error" in result.stderr:
                print("--- 错误信息 ---")
                print(result.stderr[:500])

            # 判断是否成功
            if result.returncode == 0:
                print("✅ 测试通过")
                results.append((name, "✅ 通过"))
            else:
                print("❌ 测试失败")
                results.append((name, "❌ 失败"))

        except subprocess.TimeoutExpired:

            print("❌ 超时（300秒）")
            
            results.append((name, "❌ 超时"))
        except Exception as e:
            print(f"❌ 异常: {e}")
            results.append((name, "❌ 异常"))

    print(f"\n{'='*50}")
    print(f"{language} 基准测试结果汇总")
    print(f"{'='*50}")
    for name, status in results:
        print(f"{status}  {name}")

    passed = sum(1 for _, s in results if s == "✅ 通过")
    total = len(results)
    print(f"\n{language} 成功率: {passed}/{total} ({passed/total*100:.1f}%)")
