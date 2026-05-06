# tools/real_tools.py
import os
import subprocess

def save_code(code: str, filepath: str) -> bool:
    """
    保存代码到文件
    
    参数:
        code: 代码字符串
        filepath: 文件路径
    
    返回:
        bool: 成功返回 True，失败返回 False
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        print(f"✅ 文件已保存: {filepath}")
        return True
        
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return False


def run_pytest(test_file_path: str) -> dict:
    """
    运行 pytest 测试文件
    
    参数:
        test_file_path: 测试文件路径
    
    返回:
        dict: {
            "passed": int,      # 通过的测试数
            "failed": int,      # 失败的测试数
            "output": str,      # pytest 完整输出
            "returncode": int   # 0表示全部通过
        }
    """
    try:
        # 获取测试文件所在目录（修复：正确定义 test_dir）
        test_dir = os.path.dirname(os.path.abspath(test_file_path))
        
        # 运行 pytest
        result = subprocess.run(
            ['pytest', test_file_path, '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # 解析输出
        output = result.stdout + result.stderr
        
        # 简单统计 passed/failed
        passed = output.count("PASSED")
        failed = output.count("FAILED")
        
        # 如果 returncode 为 0 且没有统计到失败，则认为全部通过
        if result.returncode == 0 and failed == 0:
            passed = 1 if passed == 0 else passed
        
        return {
            "passed": passed,
            "failed": failed,
            "output": output,
            "returncode": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 1,
            "output": "测试执行超时（超过30秒）",
            "returncode": -1
        }
    except FileNotFoundError:
        return {
            "passed": 0,
            "failed": 1,
            "output": "pytest 未安装，请运行: pip install pytest",
            "returncode": -2
        }
    except Exception as e:
        return {
            "passed": 0,
            "failed": 1,
            "output": f"运行测试时发生错误: {str(e)}",
            "returncode": -3
        }