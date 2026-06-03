def reverse_string(s):
    i, j = 0, len(s) - 1
    while i < j:
        s[i], s[j] = s[j], s[i]
        i += 1
        j -= 1

def test_case_1():
    assert reverse_string(["h","e","l","l","o"]) == ["o","l","l","e","h"]

def test_case_2():
    assert reverse_string(["a"]) == ["a"]

def test_case_3():
    assert reverse_string(["a", "b", "c"]) == ["c", "b", "a"]

def test_case_4():
    assert reverse_string(["a", "b", "c", "d", "e"]) == ["e", "d", "c", "b", "a"]

def test_case_5():
    assert reverse_string(["a", "b", "c", "d", "e", "f"]) == ["f", "e", "d", "c", "b", "a"]