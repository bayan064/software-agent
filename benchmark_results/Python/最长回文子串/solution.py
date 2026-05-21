def longest_palindrome(s):
    if not s:
        return ""
    start, end = 0, 0
    for i in range(len(s)):
        len1 = expand_around_center(s, i, i)
        len2 = expand_around_center(s, i, i + 1)
        max_len = max(len1, len2)
        if max_len > end - start:
            start = i - (max_len - 1) // 2
            end = i + max_len // 2
    return s[start:end + 1]

def expand_around_center(s, left, right):
    while left >= 0 and right < len(s) and s[left] == s[right]:
        left -= 1
        right += 1
    return right - left - 1

from solution import longest_palindrome

def test_case_1():
    assert longest_palindrome("babad") in ["bab", "aba"]
def test_case_2():
    assert longest_palindrome("cbbd") == "bb"
def test_case_3():
    assert longest_palindrome("a") == "a"
def test_case_4():
    assert longest_palindrome("") == ""
def test_case_5():
    assert longest_palindrome("abcba") == "abcba"
def test_case_6():
    assert longest_palindrome("abcdedcba") == "abcdedcba"
def test_case_7():
    assert longest_palindrome("abba") == "abba"
def test_case_8():
    assert longest_palindrome("abccba") == "abccba"
def test_case_9():
    assert longest_palindrome("abc") == "a"
def test_case_10():
    assert longest_palindrome("a") == "a"
def test_case_11():
    assert longest_palindrome("aa") == "aa"
def test_case_12():
    assert longest_palindrome("abababab") == "abababab"
def test_case_13():
    assert longest_palindrome("a"*1000) == "a"*1000
def test_case_14():
    assert longest_palindrome("a"*999 + "b") == "a"*999 + "b"
def test_case_15():
    assert longest_palindrome("a"*999 + "b" + "a"*999) == "a"*999 + "b" + "a"*999