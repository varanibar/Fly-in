from pathlib import Path
from src.file_parser import Parser, MapData

def main(path: Path) -> None:
    parser = Parser(path)
    print(parser.lines)
    print(parser.raw_data)
    map_data = Parser.get_data()


if __name__ == "__main__":
    main(Path("/home/varaniba/CODAM_CORE/Fly-in/tests/valid_maps/easy/01_linear_path.txt"))
