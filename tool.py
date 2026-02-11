import tokenize
from io import BytesIO

def remove_comments(src: str) -> str:
    tokens = tokenize.tokenize(BytesIO(src.encode('utf-8')).readline)
    result = []

    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            continue
        result.append(tok)

    return tokenize.untokenize(result).decode('utf-8')


if __name__ == "__main__":
    with open("ai.py", "r", encoding="utf-8") as f:
        src = f.read()

    cleaned = remove_comments(src)

    with open("output.py", "w", encoding="utf-8") as f:
        f.write(cleaned)
