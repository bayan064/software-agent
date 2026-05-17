# interfaces.py
# 这个文件定义所有模块之间的接口，不写具体实现

def save_code(code: str, filepath: str) -> bool:
    """
    保存代码到文件
    
    参数:
        code: 代码字符串，例如 "print('hello')" 或 "public class Main {}"
        filepath: 文件路径，例如 "output/solution.py" 或 "output/Solution.java"
    
    返回:
        bool: 成功返回 True，失败返回 False
    """
    pass


def run_tests(test_file_path: str, language: str = "Python") -> dict:
    """
    根据运行的语言（Python、Java等）执行对应的测试文件
    
    参数:
        test_file_path: 测试文件路径，例如 "output/test_solution.py"
        language: 编程语言名称，默认为 "Python"，可支持 "Java"
    
    返回:
        dict: {
            "passed": int,      # 通过的测试数
            "failed": int,      # 失败的测试数
            "output": str,      # 测试框架的完整输出日志 (Stdout/Stderr)
            "returncode": int   # 0表示全部通过，非0表示有失败或错误
        }
    """
    pass
