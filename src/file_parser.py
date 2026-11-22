from pathlib import Path
from typing import Any
from enum import StrEnum
from pydantic import BaseModel, Field, ValidationError, model_validator

import re
from pydantic_core import PydanticCustomError


GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class SyntaxErrorList(Exception):
    def __init__(self, err_list: list[SyntaxError]):
        self.err_list = err_list
        self.message = f"{RED}{BOLD}Caught {len(err_list)} Syntax Errors.{RESET}"
        super().__init__(self.message)


class SyntaxError(Exception):
    def __init__(self, index: int | None, input: str | None, type: str, message: str):
        super().__init__()
        self.index = index
        self.input = input
        self.type = type
        self.message = message

    def __str__(self) -> str:
        if self.index == None:
            return(
                F"{BOLD}{RED}  > Absent data:\n{RESET}"
                f"          {BOLD}Type:     {RESET}{self.type}\n"
                f"          {BOLD}Message:  {RESET}{self.message}\n"
            )

        return(
            f"{BOLD}{RED}  > Line {self.index}:\n{RESET}"
            f"          {BOLD}Input:    {RESET}{self.input}\n"
            f"          {BOLD}Type:     {RESET}{self.type}\n"
            f"          {BOLD}Message:  {RESET}{self.message}\n"
        )

class SyntaxConnection(BaseModel):
    start: str
    end: str
    metadata: str

    @model_validator(mode="before")
    @classmethod
    def separate_metadata(cls, data: str) -> dict[str, Any]:
        parts = data.split(maxsplit=1)
        if "-" not in parts[0]:
            raise ValueError("zones missing - ")
        zones = parts[0].split("-")
        if len(zones) != 2:
            raise ValueError("zone split != 2")
        start = zones[0]
        end = zones[1]
        print(start)
        print(end)
        metadata = parts[1]
        if metadata and not metadata.startswith("["):
            raise ValueError("metadata not found")
        return{
            "start": start,
            "end": end,
            "metadata": parts[1]
        }


class SyntaxParser:

    VALID_KEYS = ("nb_drones", "start_hub", "end_hub", "hub", "connection")
    UNIQUE_KEYS = ("nb_drones", "start_hub", "end_hub")
    ZONE_KEYS = ("start_hub", "end_hub", "hub")

    PATTERNS = {
        "key_value": r"""
            (?P<key>\w+)       # Key
            :[ ]               # Colon followed by one space
            (?P<value>\S[^:]*) # Non-empty value without additional colons
        """,
        "nb_drones": r"""
            (?P<nb_drones>\d+) # Number of drones
        """,
        "zone": r"""
            (?P<name>\S+)      # Zone name
            [ ]
            (?P<x>-?\d+)       # X coordinate
            [ ]
            (?P<y>-?\d+)       # Y coordinate
            (?:                # Optional metadata
                [ ]\[
                (?P<metadata>.*)
                \]
            )?
        """,
        "connection": r"""
            (?P<start>[^-\s]+) # Starting zone
            -
            (?P<end>[^-\s]+)   # Ending zone
            (?:                # Optional metadata
                [ ]\[
                (?P<metadata>.*)
                \]
            )?
        """,
    }

    @staticmethod
    def _match_value(
                key: str,
                value: str,
                index: int
            ) -> dict[str, Any]:

        pattern_key = "zone" if key in SyntaxParser.ZONE_KEYS else key

        match = re.fullmatch(
            SyntaxParser.PATTERNS[pattern_key],
            value,
            re.VERBOSE
        )

        if match is None:
            raise SyntaxError(
                index=index,
                input=f"{key}: {value}",
                type="formatting",
                message=f"Invalid {key} format"
            )

        return match.groupdict()

    @staticmethod
    def _validate_pair_structure(
                            line: str,
                            index: int
                        ) -> dict[str, Any]:
        pair = re.fullmatch(
                    SyntaxParser.PATTERNS["key_value"],
                    line,
                    re.VERBOSE
                )
        if pair is None:
            raise SyntaxError(
                index=index,
                input=line,
                type="formatting",
                message="Expected 'key: value' format"
            )

        return pair.groupdict()

    @staticmethod
    def _get_zone(value: str) -> str:
        parts = value.split()
        return parts[0]

    @staticmethod
    def _get_connections(value: str) -> tuple[str, str]:
        parts = value.split()
        start, end = parts[0].split("-")
        return start, end

    @staticmethod
    def get_raw_data(lines: list[str]) -> dict[str, Any]:
        raw_data: dict[str, Any] = {}
        errors_list: list[SyntaxError] = []

        # Variables for groups of data
        hubs: list[tuple[int, str]] = []
        connections: list[str] = []

        # Helper variables
        seen_keys: set[str] = set()
        zones: set[str] = set()
        first_line = 0

        for index, line in enumerate(lines, start=1):

            # Ommit comments or empty lines
            if line.startswith("#") or not line:
                continue

            first_line += 1

            # Validate key-value structure
            try:
                pair = SyntaxParser._validate_pair_structure(line, index)
            except SyntaxError as error:
                errors_list.append(error)
                continue

            key, value = pair["key"], pair["value"]

            # Validate key
            if key not in SyntaxParser.VALID_KEYS:
                errors_list.append(
                    SyntaxError(
                        index=index,
                        input=line,
                        type="invalid_key",
                        message=f"Allowed keys = {SyntaxParser.VALID_KEYS}"
                    )
                )
                continue

            # Check unique keys
            if key in SyntaxParser.UNIQUE_KEYS:
                if key in seen_keys:
                        errors_list.append(
                            SyntaxError(
                                index=index,
                                input=line,
                                type="duplicate_key",
                                message=f"{key} must be declared only once"
                            )
                        )
                        continue

                seen_keys.add(key) # if it's unique and it hasnt been seen

            # Check special condition for nb of drones (placement)
            if key == "nb_drones" and first_line != 1:
                    errors_list.append(
                        SyntaxError(
                            index=index,
                            input=line,
                            type="line_placement",
                            message="nb_drones must be declared in the first line"
                        )
                    )
                    continue

            # Validate the value and extract all the parts using the patterns
            try:
                data = SyntaxParser._match_value(key, value, index) #groupdict
            except SyntaxError as error:
                errors_list.append(error)
                continue

            # Store extracted values in raw data

            # Store nb_drones
            if key == "nb_drones":
                raw_data[key] = (index, data)

            # Store zones
            elif key in SyntaxParser.ZONE_KEYS:

                ## Zone duplicates are not allowed
                name = data["name"]
                if name in zones:
                    errors_list.append(
                        SyntaxError(
                            index=index,
                            input=line,
                            type="duplicate_zone",
                            message=f"Zone '{name}' is already defined"
                        )
                    )
                    continue

                zones.add(name) # only if unique

                ## Store hub only if the previous zone condition is met
                if key == "hub":
                    hubs.append((index, data)) #hub zones, added to a list
                else:
                    raw_data[key] = (index, data) #start and end zones, added to the dict

            # Store connection
            elif key == "connection":

                start, end = data["start"], data["end"]
                if start not in zones or end not in zones:
                    errors_list.append(
                        SyntaxError(
                            index=index,
                            input=line,
                            type="undefined_zones",
                            message=f"Connections must link previously defined zones using connection"
                        )
                    )
                    continue

                connections.append((index, data))

        # Check mandatory keys
        missing_keys = set(SyntaxParser.UNIQUE_KEYS) - raw_data.keys()

        if missing_keys:
            errors_list.append(
                SyntaxError(
                    index=None,
                    input=None,
                    type="syntax_parsing",
                    message=f"Missing mandatory keys: {missing_keys}"
                )
            )

        # If errors were found, they are raised using a custom error class
        if errors_list:
            raise SyntaxErrorList(err_list=errors_list)

        # If no errors were found
        raw_data["hubs"] = hubs #adding hubs to the dict
        raw_data["connections"] = connections #adding connections to the dict

        return raw_data


class ZoneTypes(StrEnum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zones(BaseModel):
    name: str
    x: int
    y: int
    metadata: str

    @model_validator(mode="before")
    @classmethod
    def get_parts(cls, data: str) -> dict[str, Any]:
        if " [" in data:
            split_data = data.split(" [", maxsplit=1)
            name_x_y = split_data[0]
            metadata = "[" + split_data[1]
            if "]" in metadata:
                tmp = metadata.split("]", maxsplit=1)
                if tmp[1]:
                    raise PydanticCustomError(
                        "zone_before_validator",
                        "Found arguments after metadata"
                        )

        elif "[" in data:
            raise PydanticCustomError(
                "zone_before_validator",
                "Arguments need to be separated by espaces"
                )

        else:
            raise PydanticCustomError(
                "zone_before_validator",
                "Metadata not found"
                )

        parts = name_x_y.split(maxsplit=2)

        if len(parts) != 3:
            raise PydanticCustomError(
                "zone_before_validator",
                "Not enough arguments, expected <name> <x> <y> [metadata]"
                )

        return {
            "name": parts[0],
            "x": parts[1],
            "y": parts[2],
            "metadata": metadata
        }


class Connections:
    pass


class ConfigData(BaseModel):
    nb_drones: int = Field(gt=0)
    start_hub: str
    end_hub: str
    hubs: list[Zones]
    connections: list[str]

    @model_validator(mode="before")
    @classmethod
    def process_tuple(cls, data: dict[str, Any]):
        # for
        return {
        "nb_drones": data["nb_dones"][1],
        "start_hub": data["start_hub"][1],
        "end_hub": data["end_hub"][1],
        "hubs": data["hubs"][1],
        "connections": data["connections"][1]
        }



class RawData:
    def __init__(self, file_path: Path):
        self.file_path: Path = file_path
        self.lines: list[str] = []
        self.data: dict[str, Any] = {}

    def get_lines(self) -> None:
        file = open(self.file_path, "r")
        self.lines = file.read().splitlines()
        file.close()

    def get_data(self) -> None:
        self.data = SyntaxParser.get_raw_data(self.lines)


def whole_process(file_path: Path) -> None:
    try:
        raw_data = RawData(file_path)
        raw_data.get_lines()
    except Exception as err:
        print(f"{RED}{BOLD}Caught {err.__class__.__name__}:{RESET} {err}{RESET}")
    else:
        print(f"  >> {GREEN}{BOLD}Reading successful!{RESET}")

        try:
            raw_data.get_data()
            print((raw_data.data))
        except SyntaxErrorList as syntax_errors:
            print(f"  xx {syntax_errors}")
            for err in syntax_errors.err_list:
                    print(err)

        # else:
        #     print(f"  >> {GREEN}{BOLD}Raw data obtained successfully!{RESET}")
        #     print(f"     {BOLD}Creating ConfigData...{RESET}")
        #     try:
        #         map = ConfigData(**raw_data.data)
        #     except ValidationError as pydantic_err:
        #         print((f"  xx {RED}{BOLD}Found Validation Errors:{RESET}"))
        #         for pyd_err in pydantic_err.errors():
        #             print(pyd_err)
        #             print(
        #                 f"         ________________________\n"
        #                 f"         Type:     {pyd_err["type"]}\n"
        #                 f"         Location: {pyd_err["loc"]}\n"
        #                 f"         Input:    {pyd_err["input"]}\n"
        #                 f"         Message:  {pyd_err["msg"]}\n"
        #                 )
        #     else:
        #         print(f"  >> {GREEN}{BOLD}ConfigData created successfully!{RESET}")
        #         print(map)




def test_directories(directory: Path) -> None:
    maps = Path.cwd() / directory
    path_list = sorted(maps.rglob("*.txt"))
    current_dir = None

    for file_path in path_list:
        parent_dir = file_path.parent

        if parent_dir != current_dir:
            current_dir = parent_dir
            directory = current_dir.relative_to(Path.cwd())

            print(f"\n{BLUE}{BOLD}{'=' * 60}")
            print(f"{directory}")
            print(f"{'=' * 60}{RESET}")

        print(f"\n{CYAN}{BOLD}--> {file_path.name}{RESET}")

        whole_process(file_path)
        break



def test_individual() -> None:
    file_path = Path(
        "/home/veronica-aranibar/Github/Fly-in/tests/invalid_maps/invalid_files/03_invalid_syntax.txt"
        )
    print(f"\n{BLUE}{BOLD}{'=' * 60}")
    print(f"{file_path.name}")
    print(f"{'=' * 60}{RESET}")
    whole_process(file_path)


if __name__ == "__main__":
    test_individual()

    # test_directories(Path("tests/valid_maps"))

    # test_directories(Path("tests/invalid_maps/invalid_files"))


