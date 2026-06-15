# convert_humaneval_python.py
import os
import json
import urllib.request
import gzip
import random
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def download_and_extract_humaneval():
    url = "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"
    gz_path = os.path.join(BASE_DIR, "HumanEval.jsonl.gz")

    if not os.path.exists(gz_path):
        print("🚚 正在从 GitHub 下载 HumanEval 数据集...")
        urllib.request.urlretrieve(url, gz_path)
        print("✅ 下载完成。")

    tasks = []
    with gzip.open(gz_path, 'rb') as f:
        for line in f:
            tasks.append(json.loads(line.decode('utf-8')))
    return tasks


def prepare_benchmark_data(limit=10):
    tasks = download_and_extract_humaneval()

    # 确定路径
    req_dir = os.path.normpath(os.path.join(BASE_DIR, "tests", "humaneval", "requirements"))
    eval_dir = os.path.normpath(os.path.join(BASE_DIR, "tests", "humaneval", "eval_references"))

    # 🔥 每次运行前，先清空旧的测试题目录，防止跟上一次随机抽取的题目混淆
    if os.path.exists(req_dir):
        shutil.rmtree(req_dir)
    if os.path.exists(eval_dir):
        shutil.rmtree(eval_dir)

    os.makedirs(req_dir, exist_ok=True)
    os.makedirs(eval_dir, exist_ok=True)

    # 🔥 核心修改：利用 random.sample 从 164 道官方题库中随机抽取 limit 道题
    print(f"🎲 正在从官方 {len(tasks)} 道题库中随机抽取 {limit} 道题作为本次基准测试...")
    selected_tasks = random.sample(tasks, min(limit, len(tasks)))

    selected_cases = []

    for task in selected_tasks:
        task_id = task["task_id"]  # 例如 "HumanEval/24"
        clean_id = task_id.replace("/", "_").lower()  # 转成 "humaneval_24"

        # 1. 保存 prompt 到 req_xxx.txt 供给智能体读取
        req_path = os.path.normpath(os.path.join(req_dir, f"req_{clean_id}.txt"))
        with open(req_path, "w", encoding="utf-8") as f:
            f.write(task["prompt"])

        # 2. 保存官方的标准答案/验证条件
        eval_path = os.path.normpath(os.path.join(eval_dir, f"eval_{clean_id}.json"))
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": task_id,
                "entry_point": task["entry_point"],
                "test": task["test"]
            }, f, indent=4, ensure_ascii=False)

        # 统一使用标准的正斜杠返回给主控脚本
        selected_cases.append((clean_id, req_path.replace("\\", "/"), eval_path.replace("\\", "/")))
        print(f"📝 成功抽取并转换: {task_id} -> {req_path}")

    return selected_cases


if __name__ == "__main__":
    prepare_benchmark_data(10)
