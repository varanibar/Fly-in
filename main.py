from pathlib import Path
from src.file_parser import Parser, MapData, SyntaxErrorList


GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def main(path: Path) -> None:
    try:

        parser = Parser(path)
        print(f"  >> {GREEN}{BOLD}Reading successful!{RESET}")

        map_data = parser.get_data()
        print(f"  >> {GREEN}{BOLD}Raw data obtained successfully!{RESET}")
        print(map_data)

    except SyntaxErrorList as syntax_errors:
        print(f"  xx {syntax_errors}")
        for syntax_err in syntax_errors.err_list:
            print(syntax_err)

    except Exception as err:
        print(f"{RED}{BOLD}Caught {err.__class__.__name__}:{RESET} {err}{RESET}")



if __name__ == "__main__":
    main(Path("/home/varaniba/CODAM_CORE/Fly-in/tests/invalid_maps/invalid_zones/00_pydantic_check.txt"))
