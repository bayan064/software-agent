import os

def save_code(code: str, filepath: str) -> bool:
    """
    保存代码到指定路径，处理文件夹不存在等异常。
    """
    try:
        # 确保目录存在（允许纯文件名路径）
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        return True
    except Exception as e:
        print(f"Error saving code to {filepath}: {e}")
        return False