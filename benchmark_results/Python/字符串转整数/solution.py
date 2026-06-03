def my_atoi(s):
    if not s:
        return 0
    i, sign, result = 0, 1, 0
    while i < len(s) and s[i] == ' ':
        i += 1
    if i < len(s) and (s[i] == '+' or s[i] == '-'):
        sign = -1 if s[i] == '-' else 1
        i += 1
    while i < len(s) and s[i].isdigit():
        result = result * 10 + int(s[i])
        i += 1
    return min(max(result * sign, -2**31), 2**31 - 1)