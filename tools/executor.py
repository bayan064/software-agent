import os
import subprocess
import re

def run_tests(test_file_path: str, language: str = "Python") -> dict:
    """
    根据不同的编程语言（Python/Java）运行对应的测试框架并解析结果。
    """
    try:
        abs_path = os.path.abspath(test_file_path)
        test_dir = os.path.dirname(abs_path)
        
        passed = 0
        failed = 0

        # ==================== 1. PYTHON (pytest) 运行逻辑 ====================
        if language.lower() == "python":
            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = os.pathsep.join(filter(None, [test_dir, existing_pythonpath]))

            result = subprocess.run(
                ['pytest', abs_path, '-v', '--tb=short'],
                cwd=test_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            output = result.stdout + result.stderr
            
            # 解析 passed 和 failed
            summary_match = re.search(r'(\d+) passed', output)
            if summary_match:
                passed = int(summary_match.group(1))
                
            failed_match = re.search(r'(\d+) failed', output)
            if failed_match:
                failed = int(failed_match.group(1))
                
            if result.returncode != 0 and failed == 0 and passed == 0:
                failed = 1

        # ==================== 2. JAVA (JUnit) 运行逻辑 ====================
        elif language.lower() == "java":
            # 编译 Java 测试文件以及相关的依赖（假设 JUnit 在类路径中，或执行通用的 mvn test / junit 运行器）
            # 这里先实现一个通用的 JUnit 命令行调用结构
            # 实际上多语言 Agent 可以通过编译运行一体化指令或者简易框架来完成
            result = subprocess.run(
                ['java', '-jar', 'junit-platform-console-standalone.jar', '-cp', test_dir, '-c', abs_path], 
                cwd=test_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + result.stderr
            
            # 解析 JUnit 输出结果 (例如: [  2 tests successful ]  [  0 tests failed ])
            passed_match = re.search(r'(\d+)\s+tests successful', output)
            if passed_match:
                passed = int(passed_match.group(1))
                
            failed_match = re.search(r'(\d+)\s+tests failed', output)
            if failed_match:
                failed = int(failed_match.group(1))
                
            if result.returncode != 0 and failed == 0 and passed == 0:
                failed = 1

        # ==================== 3. 未知语言处理 ====================
        else:
            return {
                'passed': 0,
                'failed': 1,
                'output': f"Unsupported language: {language}",
                'returncode': -1
            }

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
