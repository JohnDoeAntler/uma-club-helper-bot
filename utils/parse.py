def parse_only_numbers(text: str) -> int:
    ret = 0
    for ch in text:
        if ch.isdigit():
            ret = ret * 10 + int(ch)
    return ret