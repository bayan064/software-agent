import pytest

# 假设这部分代码将由 AI Agent 生成
def my_atoi(s):
    """
    题目：字符串转换整数 (atoi)
    描述：将字符串转为 32 位有符号整数。
    """
    # Agent 的代码将在此处实现
    pass

def test_atoi_basic():
    """
    测试用例 1：带空格和负号
    输入：s = "   -42" -> 预期输出：-42
    """
    assert my_atoi("   -42") == -42

def test_atoi_words():
    """
    测试用例 2：数字后跟文字
    输入：s = "4193 with words" -> 预期输出：4193
    """
    assert my_atoi("4193 with words") == 4193
