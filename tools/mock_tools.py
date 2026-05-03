# tools/mock_tools.py
"""工具函数的 Mock 版本 - 供组长开发和测试用"""

def save_code(code: str, filepath: str) -> bool:
    """
    Mock 版本：假装保存代码
    真实版本会真正写文件，这里只打印
    """
    print(f"[MOCK] 保存代码到文件: {filepath}")
    print(f"[MOCK] 代码内容预览: {code[:100]}...")
    return True  # 假装成功


def run_pytest(test_file_path: str) -> dict:
    """
    Mock 版本：假装运行测试
    真实版本会调用 pytest 命令，这里返回固定结果
    """
    print(f"[MOCK] 运行测试: {test_file_path}")
    
    # 模拟测试结果
    return {
        "passed": 3,
        "failed": 0,
        "output": "Mock: 测试全部通过",
        "returncode": 0
    }