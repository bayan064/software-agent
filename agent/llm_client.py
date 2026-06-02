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


def _extract_function_name(code: str, language: str = "Python") -> str:
    """从代码中提取第一个函数/方法名"""
    if language == "Java":
        match = re.search(r'(?:public|private|protected)\s+\w+\s+(\w+)\s*\(', code)
        if not match:
            match = re.search(r'\s+(\w+)\s*\([^)]*\)\s*\{', code)
        return match.group(1) if match else "solution"
    else:
        match = re.search(r'def\s+(\w+)\s*\(', code)
        return match.group(1) if match else "solution"


def _get_class_name(code: str) -> str:
    """从Java代码中提取类名"""
    match = re.search(r'(?:public\s+)?class\s+(\w+)', code)
    return match.group(1) if match else "Solution"


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


def _split_embedded_python_tests(code: str) -> tuple:
    """
    Split embedded pytest content from code when model returns tests in code block.
    Returns (clean_code, extracted_test_code).
    """
    if not code:
        return code, ""

    patterns = [
        r'^\s*#\s*测试代码',
        r'^\s*from\s+solution\s+import\s+\w+',
        r'^\s*import\s+pytest\b',
        r'^\s*def\s+test_\w+\s*\(',
    ]

    match_positions = []
    for pattern in patterns:
        match = re.search(pattern, code, re.MULTILINE)
        if match:
            match_positions.append(match.start())

    if not match_positions:
        return code, ""

    split_at = min(match_positions)
    clean_code = code[:split_at].rstrip()
    test_code = code[split_at:].lstrip()
    return clean_code, test_code


def _ensure_java_imports(test_code: str) -> str:
    """确保 Java 测试代码包含必要的 import 语句"""
    required_imports = [
        'import org.junit.jupiter.api.Test;',
        'import static org.junit.jupiter.api.Assertions.*;'
    ]
    
    # 检查是否已有这些导入
    missing = [imp for imp in required_imports if imp not in test_code]
    
    if missing:
        # 在 package 声明之后、类声明之前添加
        lines = test_code.split('\n')
        
        # 找到插入位置（第一个非空行，或者跳过 package 声明）
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('package'):
                insert_pos = i
                break
        
        # 插入缺失的导入
        for imp in reversed(missing):
            lines.insert(insert_pos, imp)
        
        test_code = '\n'.join(lines)
        print(f"🔧 已自动添加缺失的 JUnit 导入: {missing}")
    
    return test_code


def generate_code_and_test(requirement: str, language: str = "Python") -> tuple:
    """同时生成代码和测试用例，确保一致性"""
    
    if language == "Java":
        prompt = f"""请根据以下需求，同时生成Java代码和对应的JUnit测试用例。

【需求】
{requirement}

【严格要求 - 必须遵守】
1. 代码部分只包含类实现，绝对不能包含测试代码
2. 测试部分只包含JUnit测试用例，使用 JUnit 5 (Jupiter)
3. 代码和测试用例必须保持一致
4. 类名必须是 Solution，方法名根据功能命名

【Java代码要求】
- 使用 public class Solution
- 方法使用合适的访问修饰符
- 不需要main方法
- 绝对不要包含任何 import 语句

【JUnit测试要求】
- 测试类名为 TestSolution
- 每个测试方法必须标注 @Test
- 使用 assertArrayEquals 比较数组
- 使用 assertEquals 比较值
- 使用 assertThrows 测试异常

【测试用例要求 - 非常重要】
- 测试用例的输入必须有唯一解，除非需求明确要求测试无解情况
- 对于两数之和问题，请确保所有测试用例确实存在解
- 错误示例：输入 [2, 5, 5, 11] 且 target=10 是**有解的** (索引1和索引2都是5)，不能期望抛异常
- 正确示例：有解的情况用 assertArrayEquals 验证结果
- 正确示例：真正无解的情况（如 [1, 2, 3], target=7）才用 assertThrows 测试异常
- 注意：同一个输入中相同值但不同索引也算有效解

【输出格式 - 必须严格遵守】
<<<CODE>>>
public class Solution {{
    public int[] twoSum(int[] nums, int target) {{
        // 实现
        return new int[]{{0, 1}};
    }}
}}
<<<CODE_END>>>

<<<TEST>>>
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class TestSolution {{
    @Test
    void testCase1() {{
        Solution solution = new Solution();
        int[] result = solution.twoSum(new int[]{{2, 7, 11, 15}}, 9);
        assertArrayEquals(new int[]{{0, 1}}, result);
    }}
}}
<<<TEST_END>>>

【重要】
- 不要输出任何其他解释文字
- 代码部分绝对不能包含 import 语句
- 测试部分必须包含 import 和 static import

请生成："""
    else:
        prompt = f"""请根据以下需求，同时生成Python代码和对应的pytest测试用例。

【需求】
{requirement}

【严格要求 - 必须遵守】
1. 代码部分只包含函数实现，绝对不能包含测试代码
2. 测试部分只包含测试用例，绝对不能包含函数实现
3. 代码和测试用例必须保持一致
4. 对于两数之和这类可能有多种返回顺序的问题，测试用例应使用 sorted() 比较

【输出格式】
<<<CODE>>>
def function_name(param1, param2):
    return result
<<<CODE_END>>>

<<<TEST>>>
from solution import function_name

def test_case_1():
    assert function_name(...) == expected
<<<TEST_END>>>

【重要】
- 不要输出任何其他解释文字

请生成："""
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    raw = response.choices[0].message.content

    # 解析代码和测试
    code_match = re.search(r'<<<CODE>>>(.*?)<<<CODE_END>>>', raw, re.DOTALL)
    test_match = re.search(r'<<<TEST>>>(.*?)<<<TEST_END>>>', raw, re.DOTALL)

    code = _clean_code(code_match.group(1)) if code_match else ""
    test_code = _clean_code(test_match.group(1)) if test_match else ""
    if language == "Python":
        code = _strip_test_functions(code)
        code, embedded_tests = _split_embedded_python_tests(code)
        if not test_code and embedded_tests:
            test_code = embedded_tests
        if test_code:
            func_name = _extract_function_name(code, language)
            test_code = _strip_function_definition(test_code, func_name)
    if language == "Java" and test_code:
        test_code = _ensure_java_imports(test_code)

    if code and not test_code:
        test_code = _generate_test_only(code, language)
    return code, test_code


def _generate_test_only(code: str, language: str = "Python") -> str:
    """仅生成测试代码（备用方案）"""
    if language == "Java":
        prompt = f"""请为以下Java代码生成JUnit测试用例。

被测试的代码：
{code}

要求：
1. 使用 JUnit 5
2. 测试类名为 TestSolution
3. 必须包含 import org.junit.jupiter.api.Test;
4. 必须包含 import static org.junit.jupiter.api.Assertions.*;

只输出测试代码，不要有其他解释。

测试代码："""
    else:
        func_name = _extract_function_name(code, language)
        prompt = f"""请为以下Python代码生成pytest测试用例。

被测试的代码：
{code}

要求：
1. 只输出纯Python代码
2. 测试代码必须写成：from solution import {func_name}

测试代码："""
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    test_code = _clean_code(response.choices[0].message.content)
    
    # 确保 Java 测试代码包含必要的导入
    if language == "Java" and test_code:
        test_code = _ensure_java_imports(test_code)
    
    return test_code


def fix_code(code: str, error_log: str, test_code: str, requirement: str, language: str = "Python") -> str:
    """根据错误日志和测试用例修复代码"""
    
    if language == "Java":
        prompt = f"""以下Java代码运行测试失败，请分析并修复。

【原始需求】
{requirement}

【当前代码（Solution.java）】
{code}

【测试代码（TestSolution.java）】
{test_code}

【错误日志】
{error_log}

重要：
1. 请只修复 Solution.java 中的代码
2. 绝对不要在 Solution.java 中添加任何 import 语句
3. 确保 Solution.java 中只有类定义

要求：只输出修复后的完整 Solution.java 代码，不要有任何解释。

修复后的 Solution.java："""
    else:
        prompt = f"""以下{language}代码运行测试失败，请分析并修复。

【原始需求】
{requirement}

【当前代码】
{code}

【测试代码】
{test_code}

【错误日志】
{error_log}

要求：只输出修复后的完整{language}代码，不要有任何解释。"""
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return _clean_code(response.choices[0].message.content)


# 为了向后兼容（如果有人还在用 generate_code）
def generate_code(requirement: str, language: str = "Python") -> str:
    """已废弃：请使用 generate_code_and_test"""
    print("⚠️ 警告: generate_code 已废弃，请使用 generate_code_and_test")
    code, _ = generate_code_and_test(requirement, language)
    return code

# ============================================================
# 组合 A：分析 + 设计 核心实现
# ============================================================

def generate_design_models(requirement: str) -> dict:
    """
    根据需求自动生成系统分析与设计模型（包含类图和活动图/状态机图，采用 PlantUML 格式）
    """
    print("🤖 正在调用大模型生成设计模型...")
    
    prompt = f"""请根据以下用户需求/PRD，进行系统分析与设计，并输出对应的系统架构设计模型。

【用户需求】
{requirement}

【严格要求】
1. 你必须至少设计并输出两种图表：
   - 类图 (Class Diagram)：展示系统的核心类、属性、方法以及类之间的关系（泛化、组合、聚合、关联等）。
   - 活动图 (Activity Diagram) 或 状态机图 (State Machine Diagram)：展示核心业务流程或状态流转。
2. 图表必须严格采用 **PlantUML** 语法编写。
3. 请将图表放在指定的标记块中，不要有任何拖泥带水的解释。

【活动图 PlantUML 语法要求 - 必须严格遵守】
1. 每一行语句必须以英文分号 ; 结尾
2. 分支必须写为: if (条件?) then (标签)
3. 循环必须写为: while (条件) is (标签)
4. 标签只能用英文或简单中文，不要有特殊符号
5. 示例正确格式:
   start
   :读入数据;
   if (x > 0?) then (是)
     :处理正数;
   else (否)
     :处理负数;
   endif
   stop

【输出格式 - 必须严格遵守】
<<<CLASS_DIAGRAM>>>
@startuml
' 在此编写 PlantUML 类图代码
@endum
<<<CLASS_DIAGRAM_END>>>

<<<ACTIVITY_DIAGRAM>>>
@startuml
' 在此编写 PlantUML 活动图或状态机图代码
@endum
<<<ACTIVITY_DIAGRAM_END>>>

<<<TEXT_DESIGN>>>
### 系统分析与设计说明
（在此对系统整体架构、设计模式选择、核心模块职责进行简要的文字说明）
<<<TEXT_DESIGN_END>>>
"""

    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    
    content = response.choices[0].message.content
    
    # 提取类图
    class_match = re.search(r'<<<CLASS_DIAGRAM>>>\s*(.*?)\s*<<<CLASS_DIAGRAM_END>>>', content, re.DOTALL)
    class_diagram = class_match.group(1).strip() if class_match else ""
    if not class_diagram and "@startuml" in content:
        # 兜底：如果模型没写标签但写了 @startuml
        puml_blocks = re.findall(r'(@startuml.*?@endum)', content, re.DOTALL)
        if len(puml_blocks) > 0: class_diagram = puml_blocks[0]
        
    # 提取活动图/状态图
    activity_match = re.search(r'<<<ACTIVITY_DIAGRAM>>>\s*(.*?)\s*<<<ACTIVITY_DIAGRAM_END>>>', content, re.DOTALL)
    activity_diagram = activity_match.group(1).strip() if activity_match else ""
    if not activity_diagram and "@startuml" in content:
        puml_blocks = re.findall(r'(@startuml.*?@endum)', content, re.DOTALL)
        if len(puml_blocks) > 1: activity_diagram = puml_blocks[1]
        
    # 提取设计说明文字
    text_match = re.search(r'<<<TEXT_DESIGN>>>\s*(.*?)\s*<<<TEXT_DESIGN_END>>>', content, re.DOTALL)
    text_design = text_match.group(1).strip() if text_match else "未生成文本说明。"

    # 如果提取失败，进行二次清晰化清理
    class_diagram = _clean_code(class_diagram)
    activity_diagram = _clean_code(activity_diagram)

    return {
        "class_diagram": class_diagram,
        "activity_diagram": activity_diagram,
        "text_design": text_design
    }