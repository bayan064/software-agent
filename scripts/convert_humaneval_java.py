# convert_humaneval_java.py
import os
import json
import random
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def prepare_benchmark_data(limit=10, language="python"):
    """准备基准测试数据"""
    
    # 尝试多种文件格式
    jsonl_gz_path = os.path.join(BASE_DIR, f"humaneval_{language}.jsonl.gz")
    jsonl_path = os.path.join(BASE_DIR, f"humaneval_{language}.jsonl")
    
    tasks = []
    
    # 优先使用 .jsonl 文件（已解压）
    if os.path.exists(jsonl_path):
        print(f"📚 加载本地数据集: {jsonl_path}")
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    tasks.append(json.loads(line))
        print(f"✅ 加载完成，共 {len(tasks)} 道题")
    
    # 其次尝试 .jsonl.gz 文件
    elif os.path.exists(jsonl_gz_path):
        print(f"📚 加载本地数据集: {jsonl_gz_path}")
        import gzip
        with gzip.open(jsonl_gz_path, 'rb') as f:
            for line in f:
                tasks.append(json.loads(line.decode('utf-8')))
        print(f"✅ 加载完成，共 {len(tasks)} 道题")
    
    else:
        print(f"❌ 文件不存在: {jsonl_path} 或 {jsonl_gz_path}")
        print(f"   请将下载的 humaneval_{language}.jsonl 文件放到项目根目录")
        print("   下载地址: https://huggingface.co/datasets/THUDM/humaneval-x/tree/main/data")
        return []
    
    # 确定路径（按语言区分）
    req_dir = os.path.normpath(os.path.join(BASE_DIR, "tests", "humaneval", language, "requirements"))
    eval_dir = os.path.normpath(os.path.join(BASE_DIR, "tests", "humaneval", language, "eval_references"))

    # 清空旧目录
    if os.path.exists(req_dir):
        shutil.rmtree(req_dir)
    if os.path.exists(eval_dir):
        shutil.rmtree(eval_dir)

    os.makedirs(req_dir, exist_ok=True)
    os.makedirs(eval_dir, exist_ok=True)

    # 随机抽取
    total = len(tasks)
    print(f"🎲 正在从官方 {total} 道题库中随机抽取 {limit} 道题...")
    random.seed(42)
    selected_tasks = random.sample(tasks, min(limit, total))

    selected_cases = []

    for task in selected_tasks:
        task_id = task.get("task_id", f"{language}/unknown")
        clean_id = task_id.replace("/", "_").lower()
        
        # 保存 prompt
        req_path = os.path.normpath(os.path.join(req_dir, f"req_{clean_id}.txt"))
        with open(req_path, "w", encoding="utf-8") as f:
            f.write(task.get("prompt", ""))
        
        # 保存测试用例
        eval_path = os.path.normpath(os.path.join(eval_dir, f"eval_{clean_id}.json"))
        
        # 提取函数名
        entry_point = task.get("entry_point", "")
        if not entry_point and "declaration" in task:
            import re
            decl = task["declaration"]
            match = re.search(r'(?:public\s+static\s+)?(\w+)\s*\(', decl)
            if match:
                entry_point = match.group(1)
        
        # 处理 test 字段（可能是字符串或列表）
        test_content = task.get("test", "")
        if isinstance(test_content, list):
            test_content = "\n".join(test_content)
        
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": task_id,
                "entry_point": entry_point,
                "test": test_content,
                "declaration": task.get("declaration", "")
            }, f, indent=4, ensure_ascii=False)

        selected_cases.append((clean_id, req_path.replace("\\", "/"), eval_path.replace("\\", "/")))
        print(f"📝 成功转换: {task_id}")

    return selected_cases


if __name__ == "__main__":
    import sys
    lang = sys.argv[1] if len(sys.argv) > 1 else "python"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    cases = prepare_benchmark_data(limit=limit, language=lang)
    print(f"\n生成了 {len(cases)} 个测试用例")