from solution import two_sum

def test_case_1():
    assert sorted(two_sum([2, 7, 11, 15], 9)) == [0, 1]

def test_case_2():
    assert sorted(two_sum([3, 2, 4], 6)) == [1, 2]

def test_case_3():
    assert sorted(two_sum([3, 3], 6)) == [0, 1]

def test_case_4():
    assert sorted(two_sum([0, 4, 3, 0], 0)) == [0, 3]

def test_case_5():
    assert sorted(two_sum([], 0)) == []