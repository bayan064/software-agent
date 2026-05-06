import os
import subprocess
import re

def run_pytest(test_file_path: str) -> dict:
    """
    运行 pytest 并解析结果。
    """
    try:
        test_dir = os.path.dirname(os.path.abspath(test_file_path))
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [test_dir, existing_pythonpath]))

        # 运行 pytest 命令，捕获输出
        result = subprocess.run(
            ['pytest', test_file_path],
            cwd=test_dir,
            capture_output=True,
            text=True,
            env=env,
            timeout=30  # 防止死循环造成 Agent 卡死
        )
        
        output = result.stdout + result.stderr
        
        # 简单的正则解析（也可以用 pytest-json-report 插件，但这样更轻量）
        passed = 0
        failed = 0
        
        # 解析类似 "2 passed, 1 failed in 0.01s" 的行
        summary_match = re.search(r'(\d+) passed', output)
        if summary_match:
            passed = int(summary_match.group(1))
            
        failed_match = re.search(r'(\d+) failed', output)
        if failed_match:
            failed = int(failed_match.group(1))
            
        # 如果 pytest 崩溃或没找到用例，从 exit code 判断
        if result.returncode != 0 and failed == 0 and passed == 0:
            failed = 1 # 视为整体执行失败
            
        return {
            'passed': passed,
            'failed': failed,
            'output': output[-2000:] # 只返回最后2000字，防止 Token 溢出
        }
    except Exception as e:
        return {
            'passed': 0,
            'failed': 1,
            'output': f"Execution Error: {str(e)}"
        }