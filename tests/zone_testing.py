from src import file_parser
from pathlib import Path
import sys
from pydantic import ValidationError
from typing import Any

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"




def zone_check(file_path: Path):
    file = open(file_path, "r")
    lines = file.read().splitlines()
    file.close()
    zones: list[dict[str, Any]] = []
    for line in lines:
        match = file_parser.SyntaxParser._match_value("key_value", line, -1)
        value = match["value"]
        zone = file_parser.SyntaxParser._match_value("zone", value, -1)
        print(zone)
        zones.append(zone)
    for zone in zones:
        try:
            file_parser.Zone.model_validate(zone)

        except ValidationError as pydantic_err:
            print((f"  xx {RED}{BOLD}Found Validation Errors:{RESET}"))
            for pyd_err in pydantic_err.errors():
                print(
                    f"          Field:    {pyd_err["loc"]}\n"
                    f"          Type:     {pyd_err["type"]}\n"
                    f"          Message:  {pyd_err["msg"]}\n"
        )

    else:
        print(f"  >> {GREEN}{BOLD}ConfigData created successfully!{RESET}")


if __name__ == "__main__":
    zone_check("/home/varaniba/CODAM_CORE/Fly-in/tests/invalid_maps/invalid_zones/invalid_fields.txt")
