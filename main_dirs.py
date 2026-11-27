from pathlib import Path
from pydantic import ValidationError
import sys

#Project modules
from src.parser import Parser
from src.errors import SyntaxErrorList

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def parsing(path: Path) -> None:
    try:
        print(f"{BOLD}   Reading file...{RESET}", end="")
        parser = Parser(path)
        print(f"{GREEN}{BOLD}  >> Reading successful!{RESET}")
        print(f"{BOLD}   Parsing data...{RESET}", end="")

        map_data = parser.get_data()
        print(f"{GREEN}{BOLD}  >> Raw data obtained successfully!{RESET}")

        # map_data.show()


    except SyntaxErrorList as syntax_errors:
        print(f"{RED}{BOLD}  xx {syntax_errors}{RESET}")
        for syntax_err in syntax_errors.err_list:
            print(syntax_err)

    except ValidationError as pydantic:
        print(f"{RED}{BOLD}  xx Caught MapData error:{RESET}")
        for pydantic_err in pydantic.errors():
            print(pydantic_err)
            print(
                f"          Type:   {pydantic_err["type"]}\n"
                f"          Loc:    {pydantic_err["loc"]}\n"
                f"          Msg:    {pydantic_err["msg"]}\n"
                f"          Input:  {pydantic_err["input"]}\n"
            )

    # except Exception as err:
    #     print(f"{RED}{BOLD}Caught {err.__class__.__name__}:{RESET} {err}{RESET}")


def main():
    if len(sys.argv) != 2:
        print("Usage: <program_name> <directory>")
        sys.exit()
    directory = Path(sys.argv[1])
    print(directory)
    path_list = sorted(directory.rglob("*.txt"))
    print(path_list)
    current_dir = None
    print(f"\n{BLUE}{BOLD}{'=' * 60}")
    print(f"{directory}")
    print(f"{'=' * 60}{RESET}")

    for file_path in path_list:
        print(f"\n{CYAN}{BOLD}--> {file_path.name}{RESET}")

        parsing(file_path)


if __name__ == "__main__":
    main()
