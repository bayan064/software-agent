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
    if not raw:
        return ""
    lines = raw.split('\n')
    if lines and lines[0].strip().startswith('```'):
        lines = lines[1:]
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    return '\n'.join(lines).strip()


def _strip_test_functions(code: str) -> str:
    """移除意外混入的 pytest 测试函数"""
    lines = code.splitlines()
    cleaned = []
    skipping = False
    base_indent = 0

    for line in lines:
        if not skipping and re.match(r'^\s*def\s+test_\w+\s*\(', line):
            skipping = True
            base_indent = len(line) - len(line.lstrip())
            continue

        if skipping:
            if line.strip() == "":
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and re.match(r'^\s*(def|class)\s+', line):
                skipping = False
                cleaned.append(line)
            else:
                continue
        else:
            cleaned.append(line)

    return "\n".join(cleaned).strip()


def _strip_function_definition(code: str, func_name: str) -> str:
    """移除测试代码里误写的实现函数"""
    if not func_name:
        return code

    lines = code.splitlines()
    cleaned = []
    skipping = False
    base_indent = 0
    pattern = rf'^\s*def\s+{re.escape(func_name)}\s*\('

    for line in lines:
        if not skipping and re.match(pattern, line):
            skipping = True
            base_indent = len(line) - len(line.lstrip())
            continue

        if skipping:
            if line.strip() == "":
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and re.match(r'^\s*(def|class)\s+', line):
                skipping = False
                cleaned.append(line)
            else:
                continue
        else:
            cleaned.append(line)

    return "\n".join(cleaned).strip()


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


def generate_code_and_test(requirement: str) -> tuple:
    """同时生成代码和测试用例，确保一致性"""
    
    prompt = f"""请根据以下需求，同时生成Python代码和对应的pytest测试用例。

【需求】
{requirement}

【严格要求 - 必须遵守】
1. 代码部分只包含函数实现，绝对不能包含测试代码或"# 测试代码"等注释
2. 测试部分只包含测试用例，绝对不能包含函数实现
3. 代码和测试用例必须保持一致
4. 测试用例的期望输出必须严格基于代码的实际行为
5. 对于两数之和这类可能有多种返回顺序的问题，测试用例应使用 sorted() 比较或允许两种顺序
6. 输出格式如下，必须严格遵守：

<<<CODE>>>
def function_name(param1, param2):
    # 只有函数实现
    return result
<<<CODE_END>>>

<<<TEST>>>
from solution import function_name

def test_case_1():
    assert function_name(...) == expected

def test_case_2():
    result = function_name(...)
    assert result == expected or result == alternative_expected
<<<TEST_END>>>

【重要】
- 不要输出任何其他解释文字
- 代码部分绝对不能包含测试代码
- 测试部分绝对不能包含函数实现

请生成：
"""
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3  # 降低随机性，提高一致性
    )
    
    raw = response.choices[0].message.content
    
    # 解析代码和测试
    code_match = re.search(r'<<<CODE>>>(.*?)<<<CODE_END>>>', raw, re.DOTALL)
    test_match = re.search(r'<<<TEST>>>(.*?)<<<TEST_END>>>', raw, re.DOTALL)
    
    code = _clean_code(code_match.group(1)) if code_match else ""
    test_code = _clean_code(test_match.group(1)) if test_match else ""
    code = _strip_test_functions(code)
    
    # 从代码中提取函数名，确保测试导入正确
    if code and not test_code:
        func_name = _extract_function_name(code)
        # 如果测试代码为空，尝试单独生成
        test_code = generate_test(code)
    elif code and test_code:
        func_name = _extract_function_name(code)
        test_code = _strip_function_definition(test_code, func_name)
    
    return code, test_code


def generate_test(code: str) -> str:
    """根据代码生成测试用例（备用方案）"""
    func_name = _extract_function_name(code)
    
    prompt = f"""请为以下Python代码生成pytest测试用例。

重要规则：
1. 测试用例的期望输出必须严格基于代码的实际行为
2. 先阅读代码理解它的返回值格式
3. 对于可能有多种返回顺序的函数，使用 sorted() 比较或允许两种顺序

要求：
1. 只输出纯Python代码
2. 测试代码必须写成：from solution import {func_name}

被测试的代码：
{code}

测试代码：
"""
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return _clean_code(response.choices[0].message.content)


def fix_code(code: str, error_log: str, test_code: str, requirement: str) -> str:
    """根据错误日志和测试用例修复代码"""
    prompt = f"""以下代码运行测试失败，请分析并修复。

【原始需求】
{requirement}

【当前代码】
{code}

【测试代码（包含期望输出）】
{test_code}

【错误日志】
{error_log}

请分析：
1. 是代码错了，还是测试用例的期望值错了？
2. 如果是代码错了，修复代码
3. 如果是测试用例错了，按照原始需求修复代码（不要修改测试用例）

要求：只输出修复后的完整Python代码，不要有任何解释。
"""
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return _clean_code(response.choices[0].message.content)