# interfaces.py
# 这个文件定义所有模块之间的接口，不写具体实现

def save_code(code: str, filepath: str) -> bool:
    """
    保存代码到文件
    
    参数:
        code: 代码字符串，例如 "print('hello')"
        filepath: 文件路径，例如 "output/solution.py"
    
    返回:
        bool: 成功返回 True，失败返回 False
    """
    pass


def run_pytest(test_file_path: str) -> dict:
    """
    运行 pytest 测试文件
    
    参数:
        test_file_path: 测试文件路径，例如 "output/test_solution.py"
    
    返回:
        dict: {
            "passed": int,      # 通过的测试数
            "failed": int,      # 失败的测试数
            "output": str,      # pytest 完整输出
            "returncode": int   # 0表示全部通过
        }
    """
    pass