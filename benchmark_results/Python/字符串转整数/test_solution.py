from solution import my_atoi

def test_case_1():
    assert my_atoi("   -42") == -42

def test_case_2():
    assert my_atoi("4193 with words") == 4193

def test_case_3():
    assert my_atoi("words and 987") == 0

def test_case_4():
    assert my_atoi("-91283472332") == -2147483648

def test_case_5():
    assert my_atoi("3.14159") == 3

def test_case_6():
    assert my_atoi("   +0") == 0

def test_case_7():
    assert my_atoi("   -0") == 0

def test_case_8():
    assert my_atoi("") == 0

def test_case_9():
    assert my_atoi("   2147483647") == 2147483647

def test_case_10():
    assert my_atoi("-2147483648") == -2147483648