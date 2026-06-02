# tools/executor.py
import os
import subprocess
import re
import tempfile
import urllib.request

# JUnit 平台控制台独立 Jar 下载 URL
JUNIT_JAR_URL = "https://repo1.maven.org/maven2/org/junit/platform/junit-platform-console-standalone/1.10.2/junit-platform-console-standalone-1.10.2.jar"

def ensure_junit_jar():
    """确保 JUnit 控制台 Jar 存在，如果不存在则下载"""
    junit_jar = os.path.join(tempfile.gettempdir(), "junit-platform-console-standalone.jar")
    if not os.path.exists(junit_jar):
        print("📦 正在下载 JUnit 控制台 Jar...")
        try:
            urllib.request.urlretrieve(JUNIT_JAR_URL, junit_jar)
            print(f"✅ JUnit Jar 已下载到: {junit_jar}")
        except Exception as e:
            print(f"❌ 下载 JUnit Jar 失败: {e}")
            return None
    return junit_jar

def compile_java(java_file_path: str) -> tuple:
    """
    编译 Java 文件。
    修复点：在编译时显式添加 JUnit Jar 到 Classpath (-cp)，否则 javac 会报'找不到符号'错误。
    """
    try:
        test_dir = os.path.dirname(java_file_path)
        solution_file = os.path.join(test_dir, "Solution.java")
        
        # 1. 确保获取到 JUnit Jar 路径
        junit_jar = ensure_junit_jar()
        if not junit_jar:
            return False, "Failed to locate/download JUnit jar for compilation"

        # 2. 收集需要编译的文件
        java_files = [java_file_path]
        if os.path.exists(solution_file):
            java_files.append(solution_file)
        
        # 3. 设置类路径：Windows 使用分号 ';'，Linux/Mac 使用冒号 ':'
        cp_separator = ";" if os.name == 'nt' else ":"
        # 当前目录 (.) 和 JUnit Jar 必须都在类路径中
        classpath = f".{cp_separator}{junit_jar}"

        # 4. 执行编译命令
        cmd = ['javac', '-cp', classpath] + java_files
        
        result = subprocess.run(
            cmd,
            cwd=test_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        
        if result.returncode != 0:
            return False, result.stderr
        return True, "Compilation successful"
    except Exception as e:
        return False, str(e)

def run_java_tests(test_file_path: str) -> dict:
    """运行 JUnit 测试并解析结果"""
    try:
        test_dir = os.path.dirname(test_file_path)
        
        # 编译阶段 (已集成类路径修复)
        success, output = compile_java(test_file_path)
        if not success:
            return {
                'passed': 0,
                'failed': 1,
                'output': f"Compilation failed:\n{output}",
                'returncode': -1
            }
        
        junit_jar = ensure_junit_jar()
        if not junit_jar:
            return {'passed': 0, 'failed': 1, 'output': "JUnit jar missing", 'returncode': -1}
        
        # 运行测试
        result = subprocess.run(
            ['java', '-jar', junit_jar, '--class-path', test_dir, '--scan-class-path'],
            cwd=test_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        
        output = result.stdout + result.stderr
        passed = 0
        failed = 0
        
        # 解析 JUnit 输出结果
        passed_match = re.search(r'(\d+)\s+tests successful', output)
        if passed_match:
            passed = int(passed_match.group(1))
        
        failed_match = re.search(r'(\d+)\s+tests failed', output)
        if failed_match:
            failed = int(failed_match.group(1))
        
        # 备选解析方案
        if passed == 0 and failed == 0:
            tests_run_match = re.search(r'Tests run:\s*(\d+)', output)
            failures_match = re.search(r'Failures:\s*(\d+)', output)
            if tests_run_match and failures_match:
                total = int(tests_run_match.group(1))
                failed = int(failures_match.group(1))
                passed = total - failed
        
        return {
            'passed': passed,
            'failed': failed,
            'output': output[-8000:],
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {'passed': 0, 'failed': 1, 'output': "Execution timeout", 'returncode': -1}
    except Exception as e:
        return {'passed': 0, 'failed': 1, 'output': f"Error: {str(e)}", 'returncode': -1}

def run_pytests(test_file_path: str, language: str = "Python") -> dict:
    """根据语言运行对应的测试框架"""
    try:
        abs_path = os.path.abspath(test_file_path)
        test_dir = os.path.dirname(abs_path)
        
        if language.lower() == "python":
            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = os.pathsep.join(filter(None, [test_dir, existing_pythonpath]))

            result = subprocess.run(
                ['pytest', abs_path, '-v', '--tb=short'],
                cwd=test_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=30
            )
            output = result.stdout + result.stderr
            passed = 0
            failed = 0
            summary_match = re.search(r'(\d+) passed', output)
            if summary_match: passed = int(summary_match.group(1))
            failed_match = re.search(r'(\d+) failed', output)
            if failed_match: failed = int(failed_match.group(1))
            if result.returncode != 0 and failed == 0 and passed == 0: failed = 1
            
            return {'passed': passed, 'failed': failed, 'output': output[-2000:], 'returncode': result.returncode}

        elif language.lower() == "java":
            return run_java_tests(abs_path)

        return {'passed': 0, 'failed': 1, 'output': f"Unsupported: {language}", 'returncode': -1}
    except Exception as e:
        return {'passed': 0, 'failed': 1, 'output': str(e), 'returncode': -1}

# 兼容性别名
run_pytest = run_pytests