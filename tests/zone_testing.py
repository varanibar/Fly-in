from src import file_parser
from pathlib import Path
import sys
from pydantic import ValidationError


GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def get_files(directory: str) -> list[Path]:
    maps = Path.cwd() / directory
    return sorted(maps.rglob("*.txt"))


def parse_file(file_path: Path):
    # Try reading file first
    try:
        lines = file_parser.FileParser.read_file(file_path)
        print(f"  {GREEN}Reading successful{RESET}")
    except Exception as error:
        print(f"  {RED}File Handling Error: {error}{RESET}")

    # Check expected keys and line formatting
    else:
        try:
            raw_data = file_parser.FileParser.get_raw_data(lines)
            print(f"  {GREEN}Raw data obtained successfully{RESET}")
        except file_parser.FileParserError as syntax_error:
            print(f"  {RED}Syntax errors:{RESET}")
            for err in syntax_error.args[0]:
                print(f"    {RED}{err}{RESET}")

        #We made the checks to be sure the exception comes from
        #the check we are doing
        else:
            print("  Checking zones:")
            zone_check(raw_data["hubs"])


def zone_check(hubs: list[str]):
    for i, zone in enumerate(hubs):
        print(f"\n{CYAN}{BOLD}     Zone {i}{RESET}")
        try:
            obj = file_parser.Zones.model_validate(zone)
            print(f"      {GREEN}{zone}{RESET} -> {obj}")
        except ValidationError as zone_error:
            print(f"      {RED}{zone}{RESET} -> {len(zone_error.errors())} found")
            for idx, error in enumerate(zone_error.errors()):
                print(
                    f"         {BOLD}Error {idx}{RESET}:\n"
                    f"         Type:     {error["type"]}\n"
                    f"         Location: {error["loc"]}\n"
                    f"         Input:    {error["input"]}\n"
                    f"         Message:  {error["msg"]}\n"
                    )



if __name__ == "__main__":
    path_list = get_files(sys.argv[1])
    current_dir = None

    for file_path in path_list:

        if file_path.parent != current_dir:
            current_dir = file_path.parent
            directory = current_dir.relative_to(Path.cwd())

            print(f"\n{BLUE}{BOLD}{'=' * 60}")
            print(f"{directory}")
            print(f"{'=' * 60}{RESET}")

        print(f"\n{CYAN}{BOLD}--> {file_path.name}{RESET}")
        parse_file(file_path)

    print()
