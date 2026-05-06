import pytest

# 假设这部分代码将由 AI Agent 生成
def two_sum(nums, target):
    """
    题目：两数之和 (Two Sum)
    描述：在 nums 数组中找到两个数，使其和等于 target，并返回下标。
    """
    # Agent 的代码将在此处实现
    pass

def test_two_sum_example1():
    """
    测试用例 1：标准输入
    输入：nums = [2, 7, 11, 15], target = 9
    预期输出：[0, 1]
    """
    nums = [2, 7, 11, 15]
    target = 9
    assert two_sum(nums, target) == [0, 1]

def test_two_sum_example2():
    """
    测试用例 2：无序数组
    输入：nums = [3, 2, 4], target = 6
    预期输出：[1, 2]
    """
    nums = [3, 2, 4]
    target = 6
    assert two_sum(nums, target) == [1, 2]
