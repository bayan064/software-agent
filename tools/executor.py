import os
import subprocess
import re

def run_pytest(test_file_path: str) -> dict:
    """
    运行 pytest 并解析结果。
    """
    try:
        # 转换为绝对路径（关键修复！）
        abs_path = os.path.abspath(test_file_path)
        test_dir = os.path.dirname(abs_path)
        
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [test_dir, existing_pythonpath]))

        # 运行 pytest 命令，捕获输出
        result = subprocess.run(
            ['pytest', abs_path, '-v', '--tb=short'],  # 使用绝对路径
            cwd=test_dir,
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        
        output = result.stdout + result.stderr
        
        # 解析 passed/failed
        passed = 0
        failed = 0
        
        summary_match = re.search(r'(\d+) passed', output)
        if summary_match:
            passed = int(summary_match.group(1))
            
        failed_match = re.search(r'(\d+) failed', output)
        if failed_match:
            failed = int(failed_match.group(1))
            
        if result.returncode != 0 and failed == 0 and passed == 0:
            failed = 1
            
        return {
            'passed': passed,
            'failed': failed,
            'output': output[-2000:],
            'returncode': result.returncode
        }
    except Exception as e:
        return {
            'passed': 0,
            'failed': 1,
            'output': f"Execution Error: {str(e)}",
            'returncode': -1
        }