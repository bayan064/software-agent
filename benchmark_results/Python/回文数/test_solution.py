from solution import is_palindrome

def test_case_1():
    assert is_palindrome(121) == True

def test_case_2():
    assert is_palindrome(-121) == False

def test_case_3():
    assert is_palindrome(10) == False

def test_case_4():
    assert is_palindrome(0) == True

def test_case_5():
    assert is_palindrome(12321) == True