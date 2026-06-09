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
    修复点：强制使用UTF-8编码编译
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
        
        # 3. 设置类路径
        cp_separator = ";" if os.name == 'nt' else ":"
        classpath = f".{cp_separator}{junit_jar}"
        
        # 4. 关键修复：添加 -encoding UTF-8 参数
        cmd = ['javac', '-encoding', 'UTF-8', '-cp', classpath] + java_files
        
        print(f"🔨 编译命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=test_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",  # 输出使用UTF-8解码
            errors="replace",
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr
            print(f"❌ Java编译失败:\n{error_msg[:500]}")
            
            # 如果还是编码问题，尝试移除中文注释后重试
            if "unmappable character" in error_msg or "GBK" in error_msg:
                print("🔧 检测到编码问题，尝试移除中文注释...")
                for java_file in java_files:
                    with open(java_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 移除所有中文注释行
                    import re
                    # 移除行注释中的中文
                    lines = content.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        # 如果行注释包含中文，移除该注释
                        if '//' in line:
                            comment_start = line.index('//')
                            comment = line[comment_start+2:].strip()
                            # 如果注释包含中文，删除整个注释部分
                            if re.search(r'[\u4e00-\u9fff]', comment):
                                line = line[:comment_start].rstrip()
                        cleaned_lines.append(line)
                    
                    cleaned_content = '\n'.join(cleaned_lines)
                    
                    # 备份原文件
                    backup_file = java_file + ".bak"
                    import shutil
                    shutil.copy2(java_file, backup_file)
                    
                    with open(java_file, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)
                    
                    print(f"✅ 已清理 {java_file} 中的中文注释")
                
                # 重新编译
                result = subprocess.run(
                    cmd,
                    cwd=test_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30
                )
                
                if result.returncode == 0:
                    print("✅ 清理注释后编译成功")
                    return True, "Compilation successful after removing Chinese comments"
            
            return False, result.stderr
        
        print("✅ Java编译成功")
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

def analyze_java_test_failures(test_output: str) -> dict:
    """
    分析Java测试失败原因，提供修复建议
    """
    analysis = {
        "error_type": "unknown",
        "suggestions": [],
        "failed_tests": []
    }
    
    # 解析失败测试
    import re
    failure_pattern = r'(\w+\(\))\s+failed:\s*(.*?)(?=\n\s*\w+\(\)|$)'
    failures = re.findall(failure_pattern, test_output, re.DOTALL)
    
    for test_name, error_msg in failures:
        analysis["failed_tests"].append({"name": test_name, "error": error_msg[:200]})
        
        # 分析错误类型
        if "AssertionFailedError" in error_msg:
            if "expected:" in error_msg and "but was:" in error_msg:
                analysis["error_type"] = "assertion_mismatch"
                # 提取期望值和实际值
                import re
                expected_match = re.search(r'expected:\s*<(.+?)>', error_msg)
                actual_match = re.search(r'but was:\s*<(.+?)>', error_msg)
                if expected_match and actual_match:
                    analysis["suggestions"].append(
                        f"断言值不匹配：期望 {expected_match.group(1)}，实际 {actual_match.group(1)}。检查算法逻辑。"
                    )
        elif "NullPointerException" in error_msg:
            analysis["error_type"] = "null_pointer"
            analysis["suggestions"].append("出现空指针异常，请检查是否正确初始化对象或处理null输入。")
        elif "IndexOutOfBoundsException" in error_msg:
            analysis["error_type"] = "index_out_of_bounds"
            analysis["suggestions"].append("数组索引越界，请检查边界条件处理。")
    
    if not analysis["suggestions"]:
        analysis["suggestions"].append("请检查代码逻辑是否正确处理所有测试用例。")
    
    return analysis

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
            if summary_match: 
                passed = int(summary_match.group(1))
            failed_match = re.search(r'(\d+) failed', output)
            if failed_match: 
                failed = int(failed_match.group(1))
            if result.returncode != 0 and failed == 0 and passed == 0: 
                failed = 1
            
            return {'passed': passed, 'failed': failed, 'output': output[-2000:], 'returncode': result.returncode}

        elif language.lower() == "java":
            return run_java_tests(abs_path)

        return {'passed': 0, 'failed': 1, 'output': f"Unsupported: {language}", 'returncode': -1}
    except Exception as e:
        return {'passed': 0, 'failed': 1, 'output': str(e), 'returncode': -1}

# 兼容性别名
run_pytest = run_pytests