# main.py
import sys
from agent.llm_client import generate_code

def main():
    print("=== 代码生成智能体启动 ===")
    
    # 测试：让大模型生成一个简单的Python函数
    requirement = "写一个Python函数，输入两个数字，返回它们的和"
    
    print(f"\n需求：{requirement}")
    print("\n正在生成代码...")
    
    code = generate_code(requirement)
    
    print("\n生成的代码：")
    print("-" * 40)
    print(code)
    print("-" * 40)

if __name__ == "__main__":
    main()