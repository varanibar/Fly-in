from typing import Any
from pathlib import Path


def read_file(path: Path) -> dict[str, Any]:
    raw_data: dict[str, Any] = {}
    syntax_errors: list[str] = []

    file = (open(path, "r"))
    lines = file.read().splitlines()
    print(lines)
    for index, line in enumerate(lines, start=1):
        if line.startswith("#") or not line:
            continue
        print(line)

        if line.count(":") != 1:
            syntax_errors.append(f"Line {index}: expected 'key:value'")
            continue

        key, value = line.split(":")
        value = value.strip(" ")
        if not key or not value:
            syntax_errors.append(f"Line {index}: 'key' and 'value' must not be empty")
            continue

        print(key)
        print(value)


    print(syntax_errors)





if __name__ == "__main__":
    path = "/home/veronica-aranibar/Github/Fly-in/maps/easy/01_linear_path.txt"
    raw_data = read_file(path)

