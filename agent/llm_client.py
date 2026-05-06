# agent/llm_client.py
import os
import re
from zhipuai import ZhipuAI

print("我正在加载 llm_client.py，包名是 zhipuai")

# 从环境变量读取API Key
api_key = os.environ.get("ZHIPU_API_KEY")
if not api_key:
    raise ValueError("请设置环境变量 ZHIPU_API_KEY，例如：export ZHIPU_API_KEY='你的密钥'")

client = ZhipuAI(api_key=api_key)


def _extract_function_name(code: str) -> str:
    """从代码中提取第一个函数名"""
    match = re.search(r'def\s+(\w+)\s*\(', code)
    return match.group(1) if match else "solution"


def _clean_code(raw: str) -> str:
    """移除markdown代码块标记"""
    lines = raw.split('\n')
    if lines and lines[0].strip().startswith('```'):
        lines = lines[1:]
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    return '\n'.join(lines)


def generate_code(requirement: str) -> str:
    """根据需求生成代码"""
    prompt = f"""请根据以下需求生成Python代码。

要求：
1. 只输出纯Python代码，不要用```python```或任何其他标记包裹
2. 不要在代码前后添加任何解释文字
3. 代码必须可以直接运行

需求：{requirement}
"""
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return _clean_code(response.choices[0].message.content)


def generate_test(code: str) -> str:
    """根据代码生成测试用例"""
    func_name = _extract_function_name(code)
    
    prompt = f"""请为以下Python代码生成pytest测试用例。

要求：
1. 只输出纯Python代码，不要用```python```或任何其他标记包裹
2. 不要有任何解释文字
3. 代码必须可以被pytest直接运行
4. 测试函数命名以test_开头
5. 被测试的代码会保存在 solution.py 文件中
6. 所以测试代码必须写成：from solution import {func_name}

被测试的代码：
{code}

测试代码：
"""
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return _clean_code(response.choices[0].message.content)


def fix_code(code: str, error_log: str) -> str:
    """根据错误日志修复代码"""
    prompt = f"""以下代码运行出错，请修复代码中的问题。

要求：
1. 只输出修复后的纯Python代码，不要用```python```或任何其他标记包裹
2. 不要有任何解释文字
3. 只输出修复后的完整代码

原始代码：
{code}

错误日志：
{error_log}

修复后的代码：
"""
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return _clean_code(response.choices[0].message.content)