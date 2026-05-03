# agent/llm_client.py
import os
from zhipuai import ZhipuAI
print("我正在加载 llm_client.py，包名是 zhipuai")
# 从环境变量读取API Key
api_key = os.environ.get("ZHIPU_API_KEY")
if not api_key:
    raise ValueError("请设置环境变量 ZHIPU_API_KEY，例如：export ZHIPU_API_KEY='你的密钥'")

client = ZhipuAI(api_key=api_key)

def generate_code(requirement: str) -> str:
    """根据需求生成代码"""
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": requirement}]
    )
    return response.choices[0].message.content

def generate_test(code: str) -> str:
    """根据代码生成测试用例"""
    prompt = f"请为以下代码生成pytest测试用例：\n{code}"
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def fix_code(code: str, error_log: str) -> str:
    """根据错误日志修复代码"""
    prompt = f"以下代码运行出错：\n{code}\n\n错误日志：\n{error_log}\n\n请修复代码中的问题。"
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content