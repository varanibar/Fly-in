import pydantic
import pathlib
from pathlib import Path


#check if directory exists
def files_exist() -> bool:
    cur_dir = Path.cwd()
    maps_dir = Path(str(cur_dir) + "/maps")
    if not maps_dir.exists():
        print ("Directory not found: Place all text files in /maps")
        return False
    elif not maps_dir.is_dir():
        print ("Directory not found: /maps must be a directory")
        return False

    try:
        files = maps_dir.rglob("*.txt")
        print(type(files))
        print(files)
        for file in files:
            print(type(file))
    except Exception as err:
        print(err)
        return False
    else:
        return True





if __name__ == "__main__":
    print(files_exist())

