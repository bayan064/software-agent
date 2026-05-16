import argparse
from agent.graph import app
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="需求文件路径")
    parser.add_argument("--output", default="./output", help="输出目录")
    args = parser.parse_args()
    
    with open(args.input, "r", encoding="utf-8") as f:
        requirement = f.read()
    
    # 确保输出目录存在
    os.makedirs(args.output, exist_ok=True)
    
    # ⚠️ 关键：把输出路径传给 graph
    result = app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": requirement,
        "output_dir": args.output  
    })
    
    print(f"✅ 完成，结果保存在 {args.output}")

if __name__ == "__main__":
    main()